from sqlalchemy.orm import Session
from collections import defaultdict
from app.models.transaction import Transaction, OperationType
from app.models.position import Position


def recalc_positions(portfolio_id: int, db: Session) -> None:
    """
    Recalcula pre\u00e7o m\u00e9dio ponderado e quantidade atual
    para cada ativo da carteira, a partir do hist\u00f3rico de transa\u00e7\u00f5es.

    Algoritmo de pre\u00e7o m\u00e9dio ponderado (FIFO simplificado):
      - Compra: pm = (pm_ant * qt_ant + qt_nova * preco) / (qt_ant + qt_nova)
      - Venda:  pm n\u00e3o muda, apenas reduz quantidade
    """
    txs = (
        db.query(Transaction)
        .filter(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.date.asc(), Transaction.id.asc())
        .all()
    )

    # ticker -> {qty, avg_price, asset_type}
    state: dict[str, dict] = defaultdict(lambda: {"qty": 0.0, "avg_price": 0.0, "asset_type": ""})

    for tx in txs:
        s = state[tx.ticker]
        s["asset_type"] = tx.asset_type

        if tx.operation == OperationType.buy:
            total_cost  = s["qty"] * s["avg_price"] + tx.quantity * tx.price + tx.fees
            new_qty     = s["qty"] + tx.quantity
            s["avg_price"] = total_cost / new_qty if new_qty > 0 else 0
            s["qty"]       = new_qty
        else:  # sell
            s["qty"] = max(s["qty"] - tx.quantity, 0)
            # pm n\u00e3o altera em venda

    # Remove posi\u00e7\u00f5es zeradas do estado
    active = {k: v for k, v in state.items() if v["qty"] > 1e-9}

    # Busca posi\u00e7\u00f5es existentes no banco
    existing = {
        p.ticker: p
        for p in db.query(Position).filter(Position.portfolio_id == portfolio_id).all()
    }

    # Tickers que sumiram (zerados) -> excluir
    for ticker in list(existing.keys()):
        if ticker not in active:
            db.delete(existing[ticker])

    # Upsert
    for ticker, data in active.items():
        if ticker in existing:
            pos = existing[ticker]
            pos.quantity  = data["qty"]
            pos.avg_price = data["avg_price"]
        else:
            pos = Position(
                portfolio_id=portfolio_id,
                ticker=ticker,
                asset_type=data["asset_type"],
                quantity=data["qty"],
                avg_price=data["avg_price"],
            )
            db.add(pos)

    db.commit()
