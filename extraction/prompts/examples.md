Examples of fields from documents laid out in different ways:
<examples>
<example>
<document>
Description                Qty    Unit price    Amount
Steel ruler, 30 cm     1 gross          0.85    122.40
</document>
<line_item>{"description": "Steel ruler, 30 cm", "quantity": 144, "unit": "each", "unit_price": 0.85, "amount": 122.4}</line_item>
<why>A gross is 144 rulers, and the unit price is per ruler: 144 x 0.85 = 122.40. Not quantity 1 with unit "gross".</why>
</example>
<example>
<document>
We supplied cotton napkins (3 cases of 12) at £2.10 each, £75.60 in all.
</document>
<line_item>{"description": "Cotton napkin", "quantity": 36, "unit": "each", "unit_price": 2.1, "amount": 75.6}</line_item>
<why>Three cases of twelve is 36 napkins, priced each: 36 x 2.10 = 75.60. The pack size isn't part of the description.</why>
</example>
<example>
<document>
- half a dozen x Copper saucepan @ 31,00 = 186,00
</document>
<line_item>{"description": "Copper saucepan", "quantity": 6, "unit": "each", "unit_price": 31.0, "amount": 186.0}</line_item>
<why>Half a dozen is 6, and 31,00 is 31.00 with a decimal comma: 6 x 31.00 = 186.00.</why>
</example>
<example>
<document>
Desk fan                      4         22.00      88.00
</document>
<line_item>{"description": "Desk fan", "quantity": 4, "unit": "each", "unit_price": 22.0, "amount": 88.0}</line_item>
<why>A plain count needs no conversion. The unit is still "each": never empty, never a placeholder.</why>
</example>
<example>
<document>
KUPFERWERK HAUSRAT GMBH          Rechnung Nr. KH-2207          Datum: 03.11.2026
</document>
<fields>{"invoice_number": "KH-2207", "invoice_date": "2026-11-03"}</fields>
<why>A German supplier writes the day first: 03.11.2026 is 3 November 2026, not March 11.</why>
</example>
</examples>
