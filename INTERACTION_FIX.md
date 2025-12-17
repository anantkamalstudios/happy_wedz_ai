Issue: SQLAlchemy initialization failed with:

"Could not determine join condition between parent/child tables on relationship Vendor.interactions - there are no foreign keys linking these tables." 

Root cause:
- `Vendor` model declared `interactions = relationship('UserInteraction', back_populates='vendor')`.
- `UserInteraction` model did not have a `vendor_id` ForeignKey to `vendors.id` (it recorded only `vendor_subcategory_data_id`).
- SQLAlchemy cannot infer join condition without an FK or explicit primaryjoin.

Fix applied:
1. Added optional `vendor_id = Column(Integer, ForeignKey('vendors.id'), nullable=True)` to `apps/recommendations/models/interaction.py`.
2. Added `vendor = relationship('Vendor', back_populates='interactions')` to `UserInteraction`.
3. When enriching interactions in `apps/recommendations/routes/interactions.py`, we now set `vendor_id` on the created `UserInteraction` record when `VendorSubcategoryData` resolves to a `Vendor`.

Notes:
- The `vendor_id` column is optional to preserve the original intent of recording interactions against `vendor_subcategory_data_id` primarily.
- Database migration is required to add the `vendor_id` column in production if using a persistent DB. Running the app without migrating will raise schema errors at runtime when inserting rows; please run a migration (Alembic or equivalent) to add the new column.

Suggested migration SQL (Postgres):

ALTER TABLE user_interactions
ADD COLUMN vendor_id integer REFERENCES vendors(id);

If you want, I can prepare an Alembic revision for this change.
