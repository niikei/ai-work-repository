# Archive

Inactive durable records live here after an explicit lifecycle review.

- Projects may be archived only when `completed` or `cancelled`.
- Areas and Library entities may be archived only when `retired`.
- Logs and Inbox captures are not archived here.
- Stable IDs and document history remain unchanged.
- Use `workrepo archive ID`; do not move managed records manually.
- Use `workrepo restore ID` to reverse an archive operation.

Archive placement is organized by operation year and document type. Search includes archived records,
while the default list and generated current-state views exclude them.

Archived Project and Area directories preserve the same structure as active records: `index.md` is
the only Markdown file directly inside the Entity directory, and supporting Markdown remains in
subdirectories.
