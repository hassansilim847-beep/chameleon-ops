# Chameleon Ops
Non-browser automation ops for the Chameleon job pipeline.
Scripts read all keys/secrets from environment variables (never committed).

- apify_jobs.py — LinkedIn jobs scraper via Apify (MENA / remote / country modes)
- free_apis_jobs.py — remote jobs from free APIs (Remotive, Jobicy)
- bank_learner.py — self-learning: extracts skills from JDs into the skills bank
- cv_gen.py — dynamic CV generation from the experience bank
- notify_bots.py — Telegram bot notifications (applications log / replies)
- tg_account.py — direct Telegram account bridge over WSS (Telethon, no external server)
