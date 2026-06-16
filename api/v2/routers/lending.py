"""Lending router  -  9 endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from core.framework.scale import to_human, to_raw
from api.v2.dependencies import get_current_user, get_db, require_module
from api.v2.exceptions import InsufficientBalanceError, NotFoundError, ValidationError
from api.v2.utils import to_iso
from api.v2.schemas.lending import (
    AddCollateralRequest,
    BorrowRequest,
    LendingStats,
    LoanActionResult,
    LoanPublic,
    MyLoan,
    RepayRequest,
)

from constants.economy import MIN_COLLATERAL_RATIO

router = APIRouter(prefix="/lending", tags=["lending"], dependencies=[require_module("lending")])


@router.get("/stats", response_model=LendingStats, summary="Lending protocol stats")
async def lending_stats(user: dict = Depends(get_current_user), db=Depends(get_db)):
    """Return aggregate lending protocol statistics (guild-scoped)."""
    gid = int(user["guild_id"])
    usd = await db.fetchrow(
        """
        SELECT COUNT(*)::int AS cnt,
               COALESCE(SUM(outstanding), 0) AS total_borrowed,
               COALESCE(SUM(collateral), 0) AS total_collateral
        FROM loans
        WHERE outstanding > 0 AND guild_id = $1
        """,
        gid,
    )
    total_collateral = float(usd["total_collateral"])
    total_borrowed = float(usd["total_borrowed"])
    avg_ratio = (total_collateral / total_borrowed) if total_borrowed > 0 else 0.0

    return LendingStats(
        total_borrowed=total_borrowed,
        total_collateral=total_collateral,
        active_loans=usd["cnt"],
        avg_collateral_ratio=round(avg_ratio, 2),
    )


@router.get("/loans", response_model=list[LoanPublic], summary="Active USD loans")
async def list_loans(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Return active USD loans (guild-scoped)."""
    gid = int(user["guild_id"])
    rows = await db.fetch(
        """
        SELECT user_id, principal, outstanding, collateral, created_at
        FROM loans
        WHERE outstanding > 0 AND guild_id = $3
        ORDER BY outstanding DESC
        LIMIT $1 OFFSET $2
        """,
        limit, offset, gid,
    )
    return [
        LoanPublic(
            user_id=str(r["user_id"]),
            principal=to_human(int(r["principal"] or 0)),
            outstanding=to_human(int(r["outstanding"] or 0)),
            collateral=to_human(int(r["collateral"] or 0)),
            collateral_ratio=round(
                to_human(int(r["collateral"] or 0)) / to_human(int(r["outstanding"] or 0)), 2
            ) if (r["outstanding"] or 0) > 0 else 0.0,
            created_at=to_iso(r["created_at"]),
        )
        for r in rows
    ]


@router.post("/borrow", response_model=LoanActionResult, summary="Borrow USD")
async def borrow_usd(
    body: BorrowRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Take out a USD loan by locking collateral."""
    uid = int(user["user_id"])
    gid = int(user["guild_id"])

    if body.collateral < body.amount * MIN_COLLATERAL_RATIO:
        raise ValidationError(
            f"Collateral must be at least {MIN_COLLATERAL_RATIO}x the borrow amount."
        )

    # users.wallet / loans.* are raw NUMERIC(36,0) scaled by 10**18 --
    # convert the human-scale request amounts up front and stay in raw
    # int space for every check and write.
    amount_raw = to_raw(body.amount)
    collateral_raw = to_raw(body.collateral)

    # Check no existing loan
    existing = await db.fetchrow(
        "SELECT outstanding FROM loans WHERE user_id = $1 AND guild_id = $2",
        uid, gid,
    )
    if existing and int(existing["outstanding"]) > 0:
        raise ValidationError("You already have an active loan. Repay it first.")

    async with db.transaction():
        # Lock collateral, give loan  -  RETURNING ensures deduction succeeded
        deducted = await db.fetchrow(
            "UPDATE users SET wallet = wallet - $3 WHERE user_id = $1 AND guild_id = $2 AND wallet >= $3 RETURNING wallet",
            uid, gid, collateral_raw,
        )
        if deducted is None:
            raise InsufficientBalanceError("Insufficient USD balance for collateral.")
        await db.execute(
            """
            INSERT INTO loans (user_id, guild_id, principal, outstanding, collateral)
            VALUES ($1, $2, $3, $3, $4)
            ON CONFLICT (user_id, guild_id)
            DO UPDATE SET principal = $3, outstanding = $3, collateral = $4, last_interest = now()
            """,
            uid, gid, amount_raw, collateral_raw,
        )
        # Credit borrowed USD
        await db.execute(
            "UPDATE users SET wallet = wallet + $3 WHERE user_id = $1 AND guild_id = $2",
            uid, gid, amount_raw,
        )

    return LoanActionResult(
        success=True,
        message=f"Borrowed {body.amount} USD with {body.collateral} collateral.",
        outstanding=body.amount,
        collateral=body.collateral,
    )


@router.post("/repay", response_model=LoanActionResult, summary="Repay loan")
async def repay_loan(
    body: RepayRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Repay part or all of an active USD loan."""
    uid = int(user["user_id"])
    gid = int(user["guild_id"])

    loan = await db.fetchrow(
        "SELECT outstanding, collateral FROM loans WHERE user_id = $1 AND guild_id = $2",
        uid, gid,
    )
    if not loan or int(loan["outstanding"]) <= 0:
        raise NotFoundError("No active loan found.")

    # loans.* / users.wallet are raw NUMERIC(36,0) scaled by 10**18 --
    # compare and write in raw int space only.
    amount_raw = min(to_raw(body.amount), int(loan["outstanding"]))
    new_outstanding_raw = int(loan["outstanding"]) - amount_raw
    collateral_return_raw = 0

    async with db.transaction():
        deducted = await db.fetchrow(
            "UPDATE users SET wallet = wallet - $3 WHERE user_id = $1 AND guild_id = $2 AND wallet >= $3 RETURNING wallet",
            uid, gid, amount_raw,
        )
        if deducted is None:
            raise InsufficientBalanceError("Insufficient balance to repay.")

        if new_outstanding_raw <= 0:
            # Fully repaid: return collateral
            collateral_return_raw = int(loan["collateral"])
            await db.execute(
                "UPDATE users SET wallet = wallet + $3 WHERE user_id = $1 AND guild_id = $2",
                uid, gid, collateral_return_raw,
            )
            await db.execute(
                "UPDATE loans SET outstanding = 0, collateral = 0 WHERE user_id = $1 AND guild_id = $2",
                uid, gid,
            )
        else:
            await db.execute(
                "UPDATE loans SET outstanding = $3 WHERE user_id = $1 AND guild_id = $2",
                uid, gid, new_outstanding_raw,
            )

    repaid_h = to_human(amount_raw)
    collateral_return_h = to_human(collateral_return_raw)
    return LoanActionResult(
        success=True,
        message=f"Repaid {repaid_h} USD." + (f" Collateral of {collateral_return_h} returned." if collateral_return_raw else ""),
        outstanding=to_human(max(new_outstanding_raw, 0)),
        collateral=to_human(int(loan["collateral"])) if new_outstanding_raw > 0 else 0.0,
    )


@router.post("/add-collateral", response_model=LoanActionResult, summary="Add collateral")
async def add_collateral(
    body: AddCollateralRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Add additional collateral to an existing loan."""
    uid = int(user["user_id"])
    gid = int(user["guild_id"])

    loan = await db.fetchrow(
        "SELECT outstanding, collateral FROM loans WHERE user_id = $1 AND guild_id = $2",
        uid, gid,
    )
    if not loan or int(loan["outstanding"]) <= 0:
        raise NotFoundError("No active loan found.")

    # users.wallet / loans.collateral are raw 10**18-scaled columns.
    amount_raw = to_raw(body.amount)

    async with db.transaction():
        deducted = await db.fetchrow(
            "UPDATE users SET wallet = wallet - $3 WHERE user_id = $1 AND guild_id = $2 AND wallet >= $3 RETURNING wallet",
            uid, gid, amount_raw,
        )
        if deducted is None:
            raise InsufficientBalanceError("Insufficient wallet balance.")
        await db.execute(
            "UPDATE loans SET collateral = collateral + $3 WHERE user_id = $1 AND guild_id = $2",
            uid, gid, amount_raw,
        )

    new_collateral_h = to_human(int(loan["collateral"]) + amount_raw)
    return LoanActionResult(
        success=True,
        message=f"Added {body.amount} collateral.",
        outstanding=to_human(int(loan["outstanding"])),
        collateral=new_collateral_h,
    )


@router.get("/my-loans", response_model=list[MyLoan], summary="My active loans")
async def my_loans(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Return the authenticated user's active loans (USD and SUN)."""
    uid = int(user["user_id"])
    gid = int(user["guild_id"])
    result: list[MyLoan] = []

    usd_loan = await db.fetchrow(
        "SELECT principal, outstanding, collateral, last_interest, created_at "
        "FROM loans WHERE user_id = $1 AND guild_id = $2 AND outstanding > 0",
        uid, gid,
    )
    if usd_loan:
        o = to_human(int(usd_loan["outstanding"] or 0))
        c = to_human(int(usd_loan["collateral"] or 0))
        result.append(MyLoan(
            loan_type="usd",
            principal=to_human(int(usd_loan["principal"] or 0)),
            outstanding=o,
            collateral=c,
            collateral_ratio=round(c / o, 2) if o > 0 else 0.0,
            last_interest=to_iso(usd_loan["last_interest"]),
            created_at=to_iso(usd_loan["created_at"]),
        ))

    return result
