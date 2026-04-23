## Crelate RSS → LinkedIn Job Wrapping XML

This repo generates a LinkedIn-compatible **Basic Jobs XML** feed from a Crelate job board **RSS** feed. It lines up with the same shape as LinkedIn’s **Jobs XML Development Guide** (e.g. Version 1.2 PDF) and the official “example” feed: a root `<source>`, with one `<job>` per posting and fields like `partnerJobId`, `company`, `title`, `description`, `applyUrl`, `companyId`, and `location`.

### How this maps to the PDF / Word “Sample XML Feed”

If you have **LinkedIn_Jobs_XML_Development_Guide.pdf** and **Sample XML Feed.docx**:

- **Field coverage**: The generator outputs the **mandatory** core set (per the guide): internal job id, company name, title, description, apply URL, LinkedIn company id, and location. The Word sample also shows optional blocks (industry codes, salary, `workplaceTypes`, etc.). You do not need those for a valid Basic feed; add them in Crelate/ATS or extend the script only if the client wants richer targeting.
- **Word sample**: Treat the long sample as **illustrative**. Some lines in the salary section use bad pseudo-CDATA (e.g. `![CDATA[` instead of `<![CDATA[`). Use the **Example XML Feed** in the PDF (or Microsoft Learn) for a clean template.
- **Apply URLs**: The guide stresses **no redirect chains** to the apply destination. Crelate’s job links should be direct to the posting. A Word appendix sometimes describes apply URLs with a `https://www.` prefix; Crelate uses `https://jobs.crelate.com/...` (no `www`). If ingestion validation ever complains, that’s a quick question for LinkedIn support—many live ATS links are not `www.`.
- **posterEmail**: The v1.2 PDF’s short example does not show `posterEmail`; your org’s current ingestion rules may still ask for it. The script includes `<posterEmail>` only when you set `posterEmail` in the config (omitted if empty).

### What you provide

- **Crelate RSS URL**: e.g. `https://jobs.crelate.com/portal/spcgroup/rss`
- **LinkedIn companyId**: (Swift Placement) **`73248907`**
- **Poster email**: **`jeff@swiftpcgroup.com`** (in `config.feed.json` for automated deploy; use a different local `config.json` for experiments if you want, see `.gitignore`)

For this client, the committed **`config.feed.json`** already includes RSS URL, company id, and poster email. Edit that file to change the source or company metadata.

### Hooking the feed up in Recruiter (from the customer guide)

1. As an **Admin**, go to **Product settings** → **Job posting** → under **“ATS Sources for Automated Job Postings”** choose **View/Edit** → **Add new ATS source**.
2. In **“Select your ATS”**, pick **LinkedIn Jobs XML** (naming can vary slightly by contract).
3. **Job source URL**: the public HTTPS URL of the generated `linkedin-jobs.xml`.
4. Choose the **company page** jobs should post under.
5. If apply URLs need a **source attribution** parameter, add it in the UI when LinkedIn shows that step (or per your ATS).
6. **Job Slot** contracts (utilization in Product settings): the PDF says to **open a Recruiter support ticket** to enable XML job posting. **Job Post** contracts can often use the self-service flow above.

**Operations (from the guide / FAQs):** LinkedIn **scrapes feeds about every 6 hours**; hosting the file at a **stable public URL** (HTTPS) is required. If the file is behind a tight firewall, the docs mention allowlisting **54.241.12.30**. The feed must be a **full snapshot** of jobs to ingest, not a delta of changes.

### Public HTTPS feed URL (GitHub Pages, automated)

This repo is set up to publish a **static** `linkedin-jobs.xml` on **GitHub Pages** using **GitHub Actions** (builds on every push to `main` / `master` and on a **6-hour** schedule). No separate server to run.

1. **Push** this repository to GitHub (same name is fine, e.g. `xml-job`).
2. In the repo: **Settings → Pages → Build and deployment**: set **Source** to **Deploy from a branch**, then choose branch **`gh-pages`** and folder **`/ (root)`** (the workflow creates/updates that branch for you; run **Actions** once if needed: **Actions → “Deploy LinkedIn job feed” → Run workflow**).
3. Your **Job source URL** for Recruiter will be:
   - **`https://<your-github-username>.github.io/<repository-name>/linkedin-jobs.xml`**
   - Example: if the repo is `github.com/brandonclark/xml-job`, the feed is  
     **`https://brandonclark.github.io/xml-job/linkedin-jobs.xml`**
4. The root URL (`.../index.html`) is a short human-readable blurb; LinkedIn only needs the `linkedin-jobs.xml` link.

**Note:** If the repository is **private**, GitHub’s Pages availability depends on your org/plan. For a public feed URL you can also make the repo **public** (the XML is public on LinkedIn anyway) or use another host; the workflow file is a template you can adapt.

### Quick start (local)

1) For local runs, copy `config.feed.json` to `config.json` and adjust if needed, or use `config.feed.json` directly.

2) Generate XML:

```bash
python3 ./li_feed.py --config ./config.feed.json --out ./public/linkedin-jobs.xml
```

3) Serve locally (for validation):

```bash
python3 -m http.server --directory public 8080
```

Your feed URL (local) will be `http://localhost:8080/linkedin-jobs.xml`.

