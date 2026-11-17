# Reference intake: how owner images are preserved (Supervisor procedure)

Owner reference images are the primary target, so every image the owner sends is committed to the repository the
same day; GitHub (plus the backups in DELIVERY_PLAN §8) is the durable store, never the session container.

1. **Where:** `assets/characters/<character>/references/uploads/NN_<what>.<ext>` (never edited afterwards), with a
   `README.md` row per file. Shared/multi-character references go to `assets/references/owner_uploads/` (`docs/references/` is frozen and rejects new files, even in subfolders).
2. **When images arrive in a message that starts a turn**, the session stores them under its `images/` folder: copy
   them as-is (byte-exact, original format).
3. **When images arrive mid-turn** (while the Supervisor is working), the session does not write them to disk. They are
   still in the session's conversation record as image attachments: the Supervisor extracts them byte-exact
   (base64-decoded, de-duplicated by SHA-256) and commits them. The owner never needs to resend.
4. Verify: open a thumbnail sheet of the extracted files and match them to the owner's message before committing;
   record the count and SHA-256 in the commit message.
5. Push to `staging` and `main` immediately (docs/assets only, no gate tier beyond links); the next verified backup
   then holds them too.
