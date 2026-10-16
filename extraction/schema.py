"""What we keep from each supplier document.

A field the document doesn't state is None: never a guess.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Metadata(Strict):
    doc_type: Literal["invoice", "credit_note", "other", "unclear"]
    doc_type_detail: str | None = Field(description="What the document is, only when doc_type is other or unclear")
    supplier_name: str


class LineItem(Strict):
    description: str
    quantity: float
    unit: str
    unit_price: float
    amount: float


class Document(Strict):
    supplier_name: str
    invoice_number: str | None
    invoice_date: str | None
    due_date: str | None
    payment_terms: str | None
    po_number: str | None
    currency: str | None
    line_items: list[LineItem]
    subtotal: float | None
    tax: float | None
    shipping: float | None
    stated_total: float | None
