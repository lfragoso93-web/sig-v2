from datetime import date
import pytest
from sqlalchemy import select

from app.core.access_context import PortfolioAccessContext, PortfolioAccessDenied
from app.models.fixed_income_contract import FixedIncomeContract
from app.models.portfolio import Portfolio
from app.schemas.fixed_income_contract import FixedIncomeContractCreate
from app.schemas.transaction import TransactionCreate
from app.routers.fixed_income_contracts import (
    get_fixed_income_contracts,
    post_fixed_income_contract,
)
from app.services.fixed_income_contract_service import (
    FixedIncomeContractNotFound,
    READ_FIXED_INCOME_CONTRACTS,
    list_fixed_income_contracts,
    require_fixed_income_contract,
)
from app.services.transaction_write_service import (
    TransactionWriteError,
    add_transaction_record,
)


def _contract_payload(**overrides) -> FixedIncomeContractCreate:
    values = {
        "display_name": "CDB teste",
        "product_type": "CDB",
        "issuer": "Banco Exemplo",
        "indexer": "CDI",
        "rate_value": "110",
        "rate_unit": "PERCENT_OF_INDEXER",
        "maturity_date": "2028-12-31",
        "liquidity_type": "AT_MATURITY",
        "tax_exempt": False,
        "currency": "brl",
    }
    values.update(overrides)
    return FixedIncomeContractCreate(**values)


@pytest.mark.parametrize(
    ("product_type", "submitted_tax_value", "expected_tax_value"),
    [
        ("CDB", True, False),
        ("RDB", True, False),
        ("LCI", False, True),
        ("LCA", False, True),
        ("DEBENTURE", True, False),
        ("DEBENTURE_INCENTIVADA", False, True),
    ],
)
def test_tax_treatment_is_derived_from_product_type(
    product_type, submitted_tax_value, expected_tax_value
) -> None:
    contract = _contract_payload(
        product_type=product_type, tax_exempt=submitted_tax_value
    )

    assert contract.tax_exempt is expected_tax_value


@pytest.mark.asyncio
async def test_contract_create_list_and_link_transaction(db, portfolio, user) -> None:
    created = await post_fixed_income_contract(
        portfolio.id,
        _contract_payload(),
        db,
        user,
    )

    assert created.portfolio_id == portfolio.id
    assert created.display_name == "CDB teste"
    assert created.currency == "BRL"

    listed = await get_fixed_income_contracts(portfolio.id, db, user)
    assert [item.id for item in listed] == [created.id]

    tx = await add_transaction_record(
        db,
        portfolio_id=portfolio.id,
        payload=TransactionCreate(
            ticker="CDB TESTE",
            asset_type="RENDA_FIXA",
            operation="buy",
            quantity=1,
            price=1000,
            fees=0,
            date=date(2026, 10, 17),
            fixed_income_contract_id=created.id,
        ),
    )
    await db.commit()
    await db.refresh(tx)

    assert tx.fixed_income_contract_id == created.id
    assert created.display_name == "CDB teste"


@pytest.mark.asyncio
async def test_transaction_writer_creates_contract_and_transaction_together(
    db, portfolio
) -> None:
    tx = await add_transaction_record(
        db,
        portfolio_id=portfolio.id,
        payload=TransactionCreate(
            ticker="CDB ATOMICO",
            asset_type="RENDA_FIXA",
            operation="buy",
            quantity=1,
            price=1000,
            date=date(2026, 10, 17),
            fixed_income_contract=_contract_payload(display_name="CDB atomico"),
        ),
        flush=True,
    )
    await db.commit()

    assert tx.fixed_income_contract_id is not None
    contract = await db.get(FixedIncomeContract, tx.fixed_income_contract_id)
    assert contract is not None
    assert contract.portfolio_id == portfolio.id
    assert contract.display_name == "CDB atomico"


@pytest.mark.asyncio
async def test_transaction_writer_reuses_only_equivalent_contracts_in_portfolio(
    db, portfolio
) -> None:
    first = await add_transaction_record(
        db,
        portfolio_id=portfolio.id,
        payload=TransactionCreate(
            ticker="CDB XP 110 CDI",
            asset_type="RENDA_FIXA",
            operation="buy",
            quantity=1,
            price=1000,
            date=date(2026, 10, 18),
            fixed_income_contract=_contract_payload(display_name="CDB XP 110 CDI"),
        ),
        flush=True,
    )
    equivalent = await add_transaction_record(
        db,
        portfolio_id=portfolio.id,
        payload=TransactionCreate(
            ticker="CDB XP 110 CDI",
            asset_type="RENDA_FIXA",
            operation="buy",
            quantity=2,
            price=1000,
            date=date(2026, 10, 18),
            fixed_income_contract=_contract_payload(
                display_name=" cdb   xp 110 cdi ", issuer=" BANCO   EXEMPLO "
            ),
        ),
        flush=True,
    )
    different_terms = await add_transaction_record(
        db,
        portfolio_id=portfolio.id,
        payload=TransactionCreate(
            ticker="CDB XP 110 CDI",
            asset_type="RENDA_FIXA",
            operation="buy",
            quantity=1,
            price=1000,
            date=date(2026, 10, 18),
            fixed_income_contract=_contract_payload(
                display_name="CDB XP 110 CDI", rate_value="112"
            ),
        ),
        flush=True,
    )

    assert first.fixed_income_contract_id == equivalent.fixed_income_contract_id
    assert different_terms.fixed_income_contract_id != first.fixed_income_contract_id
    contracts = (await db.execute(select(FixedIncomeContract))).scalars().all()
    assert len(contracts) == 2


@pytest.mark.asyncio
async def test_transaction_writer_reuses_legacy_issuer_when_title_name_contains_it(
    db, portfolio
) -> None:
    legacy = await add_transaction_record(
        db,
        portfolio_id=portfolio.id,
        payload=TransactionCreate(
            ticker="CDB BANCO EXEMPLO",
            asset_type="RENDA_FIXA",
            operation="buy",
            quantity=1,
            price=1000,
            date=date(2026, 10, 18),
            fixed_income_contract=_contract_payload(
                display_name="CDB Banco Exemplo 110 CDI"
            ),
        ),
        flush=True,
    )
    without_separate_issuer = await add_transaction_record(
        db,
        portfolio_id=portfolio.id,
        payload=TransactionCreate(
            ticker="CDB BANCO EXEMPLO",
            asset_type="RENDA_FIXA",
            operation="buy",
            quantity=2,
            price=1000,
            date=date(2026, 10, 18),
            fixed_income_contract=_contract_payload(
                display_name="cdb banco exemplo 110 cdi", issuer=None
            ),
        ),
        flush=True,
    )

    assert legacy.fixed_income_contract_id == without_separate_issuer.fixed_income_contract_id


@pytest.mark.asyncio
async def test_transaction_writer_never_reuses_equivalent_contract_across_portfolios(
    db, portfolio
) -> None:
    first = await add_transaction_record(
        db,
        portfolio_id=portfolio.id,
        payload=TransactionCreate(
            ticker="CDB XP 110 CDI",
            asset_type="RENDA_FIXA",
            operation="buy",
            quantity=1,
            price=1000,
            date=date(2026, 10, 18),
            fixed_income_contract=_contract_payload(display_name="CDB XP 110 CDI"),
        ),
        flush=True,
    )
    other_portfolio = Portfolio(
        user_id=portfolio.user_id, name="Outra carteira", description=""
    )
    db.add(other_portfolio)
    await db.flush()
    second = await add_transaction_record(
        db,
        portfolio_id=other_portfolio.id,
        payload=TransactionCreate(
            ticker="CDB XP 110 CDI",
            asset_type="RENDA_FIXA",
            operation="buy",
            quantity=1,
            price=1000,
            date=date(2026, 10, 18),
            fixed_income_contract=_contract_payload(display_name="cdb xp 110 cdi"),
        ),
        flush=True,
    )

    assert first.fixed_income_contract_id != second.fixed_income_contract_id
    first_contract = await db.get(FixedIncomeContract, first.fixed_income_contract_id)
    second_contract = await db.get(FixedIncomeContract, second.fixed_income_contract_id)
    assert first_contract is not None and first_contract.portfolio_id == portfolio.id
    assert second_contract is not None and second_contract.portfolio_id == other_portfolio.id


@pytest.mark.asyncio
async def test_transaction_writer_rejects_nested_contract_for_other_asset_class(
    db, portfolio
) -> None:
    with pytest.raises(TransactionWriteError, match="RENDA_FIXA"):
        await add_transaction_record(
            db,
            portfolio_id=portfolio.id,
            payload=TransactionCreate(
                ticker="PETR4",
                asset_type="ACAO",
                operation="buy",
                quantity=1,
                price=10,
                date=date(2026, 10, 17),
                fixed_income_contract=_contract_payload(),
            ),
        )

    assert len(db.new) == 0


@pytest.mark.asyncio
async def test_contract_is_not_visible_from_another_portfolio(db, portfolio, user) -> None:
    created = await post_fixed_income_contract(
        portfolio.id,
        _contract_payload(),
        db,
        user,
    )

    with pytest.raises(FixedIncomeContractNotFound):
        await require_fixed_income_contract(
            db,
            portfolio_id=portfolio.id + 1,
            contract_id=created.id,
        )


@pytest.mark.asyncio
async def test_transaction_writer_rejects_contract_from_another_portfolio(
    db, portfolio, user
) -> None:
    created = await post_fixed_income_contract(
        portfolio.id,
        _contract_payload(),
        db,
        user,
    )

    with pytest.raises(TransactionWriteError, match="nao encontrado"):
        await add_transaction_record(
            db,
            portfolio_id=portfolio.id + 1,
            payload=TransactionCreate(
                ticker="CDB TESTE",
                asset_type="RENDA_FIXA",
                operation="buy",
                quantity=1,
                price=1000,
                date=date(2026, 10, 17),
                fixed_income_contract_id=created.id,
            ),
        )


@pytest.mark.asyncio
async def test_transaction_writer_rejects_contract_for_other_asset_class(
    db, portfolio, user
) -> None:
    created = await post_fixed_income_contract(
        portfolio.id,
        _contract_payload(),
        db,
        user,
    )

    with pytest.raises(TransactionWriteError, match="RENDA_FIXA"):
        await add_transaction_record(
            db,
            portfolio_id=portfolio.id,
            payload=TransactionCreate(
                ticker="PETR4",
                asset_type="ACAO",
                operation="buy",
                quantity=1,
                price=10,
                date=date(2026, 10, 17),
                fixed_income_contract_id=created.id,
            ),
        )


@pytest.mark.parametrize(
    ("indexer", "rate_unit"),
    [
        ("CDI", "ANNUAL_PERCENT"),
        ("PREFIXADO", "PERCENT_OF_INDEXER"),
        ("IPCA_PLUS", "ANNUAL_PERCENT"),
    ],
)
def test_contract_rejects_rate_unit_mismatch(indexer, rate_unit) -> None:
    with pytest.raises(ValueError, match="rate_unit"):
        _contract_payload(indexer=indexer, rate_unit=rate_unit)


def test_contract_requires_rate_value_and_unit_together() -> None:
    with pytest.raises(ValueError, match="provided together"):
        _contract_payload(rate_unit=None)


@pytest.mark.asyncio
async def test_contract_requires_owned_portfolio_permission(db, portfolio, user) -> None:
    access = PortfolioAccessContext.for_user(
        user_id=user.id + 1,
        portfolio_id=portfolio.id,
        permissions=frozenset({READ_FIXED_INCOME_CONTRACTS}),
    )
    with pytest.raises(PortfolioAccessDenied):
        await list_fixed_income_contracts(db, access)
