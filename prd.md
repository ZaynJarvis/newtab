# New Tab: Chrome New Tab Indexer + Local Vector Store

TL;DR

A Chrome extension that automatically indexes the content of every unique webpage you visit (including path and query string), generates keywords and descriptions using an LLM, and stores both keyword and vector representations locally. Instantly search your personal web history from a new tab, retrieving relevant pages by keyword or semantic similarity—all with privacy and speed.

---

## Goals

### User Goals

* Instantly recall any previously visited webpage by keyword or semantic search from the new tab.

* Maintain full control over what is indexed and stored locally, with easy privacy management.

* Experience fast, accurate search results without sending browsing data to the cloud.

* Seamlessly index and retrieve content from dynamic URLs (including path and query).

* Enjoy a frictionless, non-intrusive background experience.

### Non-Goals

* No cloud-based storage or remote syncing of user data.

* No support for team or shared workspaces in this version.

* No advanced analytics or visualization of browsing patterns (beyond basic search and recall).

---

## User Stories

**Personas:**

* Researcher

* Engineer

* Product Manager (PM)

**Researcher**

* As a Researcher, I want every article and paper I visit to be indexed with keywords, so that I can quickly find them later by topic.

* As a Researcher, I want to exclude sensitive or private sites from indexing, so that my confidential work is not stored.

* As a Researcher, I want to search my web history semantically from the new tab, so that I can recall relevant sources even if I forget the exact title.

**Engineer**

* As an Engineer, I want code documentation and Stack Overflow pages to be indexed with their unique URLs (including query strings), so that I can find the exact solution I saw before.

* As an Engineer, I want to see a summary or description of each result, so that I can quickly identify the right page.

* As an Engineer, I want to delete or edit indexed entries, so that my local database stays relevant.

**Product Manager**

* As a PM, I want to search for competitor product pages I’ve visited, so that I can quickly reference them in meetings.

* As a PM, I want the extension to work in the background without slowing down my browsing, so that my workflow is uninterrupted.

* As a PM, I want to be notified if a page fails to index, so that I can take action if needed.

---

## Functional Requirements

* **Indexing Pipeline (Priority: High)**

  * **URL Normalization:** Capture and store full URLs, including path and query string, to distinguish unique pages.

  * **Content Extraction:** Extract main content from each visited page using a content script.

  * **LLM Keyword/Description Generation:** Use an LLM API to generate a concise set of keywords and a short description for each page.

  * **Embedding API Call:** Call a embedding API to generate vector embeddings for each page.

  * **Vector Upsert:** Store the generated vector in a local vector database (e.g., Qdrant or similar).

  * **Keyword Indexing:** Store keywords and descriptions in a local keyword-searchable index (e.g., SQLite FTS5 or Typesense).

* **Retrieval & Search (Priority: High)**

  * **Keyword Search Endpoint:** Support fast, ES-like keyword search over indexed pages.

  * **Vector Search Endpoint:** Support semantic search using vector similarity.

  * **Combined Search UI:** Present results in the new tab with relevance ranking.

* **User Controls & Privacy (Priority: Medium)**

  * **Indexing Exclusion:** Allow users to exclude specific domains or URLs from indexing.

  * **Entry Deletion/Editing:** Enable users to delete or edit indexed entries.

  * **Permissions Management:** Clearly prompt for and explain required permissions.

* **Utility & Maintenance (Priority: Medium)**

  * **Database Backup/Restore:** Allow users to export and import their local index.

  * **Error Handling & Logging:** Notify users of indexing failures and log errors locally.

---

## User Experience

**Entry Point & First-Time User Experience**

* Users discover the extension via the Chrome Web Store or direct install link.

* On first run, a welcome page explains the extension’s purpose, privacy guarantees, and required permissions (tabs, activeTab, storage).

* Users are guided through a short onboarding:

  * Option to exclude domains from indexing.

  * Option to import/export previous index (if available).

  * Confirmation of local-only data storage.

**Core Experience**

* **Step 1:** User browses the web as usual.

  * The extension’s content script detects page loads and extracts main content.

  * Minimal UI interference; a small icon indicates indexing status.

* **Step 2:** Background service worker sends content to the LLM API for keyword/description generation.

  * Handles API errors gracefully; retries or notifies user if needed.

* **Step 3:** Mock embedding API is called to generate a vector (TODO: integrate real embedding).

  * Vector and keywords are upserted into the local backend (vector DB + keyword index).

* **Step 4:** User opens a new tab (extension overrides default new tab).

  * Search bar is presented at the top, with suggestions as the user types.

  * User enters a keyword or phrase; results are fetched from both keyword and vector indexes.

  * Results are displayed as cards:

    * Title, description, URL, keywords, favicon, and quick actions (open, delete, edit).

* **Step 5:** User clicks a result to open the page in a new tab.

  * Option to delete or edit the entry directly from the result card.

**Advanced Features & Edge Cases**

* Power users can bulk delete or export their index.

* If a page fails to index (e.g., due to LLM API error), a non-intrusive notification is shown.

* If the local DB reaches capacity (e.g., 1000 docs), use ARC to remove records and prompt user to clean up or export. 

* Handles dynamic URLs and query strings as unique entries.

**UI/UX Highlights**

* High-contrast, accessible color scheme.

* Responsive layout for different screen sizes.

* Clear permission prompts and privacy explanations.

* Minimalist, distraction-free new tab UI.

* Keyboard navigation and search shortcuts.

---

## Narrative

Every day, Alex—a busy product manager—juggles dozens of tabs, researching competitors, reading documentation, and referencing past project pages. Weeks later, Alex struggles to recall a specific competitor’s pricing page, remembering only a vague feature mentioned. Instead of sifting through browser history or bookmarks, Alex opens a new tab. The search bar, powered by New Tab, instantly surfaces the exact page using a few keywords and a semantic search. The result card shows a concise description and the original URL, letting Alex jump right back in. With all data stored locally, Alex’s privacy is never compromised. Over time, Alex spends less time searching and more time building, confident that every important page is just a search away.

---

## Success Metrics
### Technical Metrics

* Indexing latency per page (<2 seconds)

* Search response time (<1 second)

* Error rate for indexing and search (<2%)

### Tracking Plan

* Extension installed/uninstalled

* First-run onboarding completed

* Page indexed (success/failure)

* Search performed (keyword/vector)

* Result clicked/opened

* Entry deleted/edited

* Privacy setting changed

* Database export/import

---

## Technical Considerations

### Technical Needs

* **Chrome Extension (MV3):**

  * Service worker for background tasks (indexing, API calls)

  * Content script for content extraction

  * New tab override for search UI

* **Local Backend Service:**

  * REST API for upsert/search/delete

  * Vector DB (Qdrant or similar, locally deployable)

  * Keyword index (SQLite FTS5 or Typesense)

  * Data model:

    * URL (full, including path+query)

    * Title

    * Description

    * Keywords

    * Vector embedding

    * Favicon

    * Timestamp

* **Mock Embedding API:**

  * Placeholder endpoint for embedding generation (TODO: integrate real embedding function)

### Integration Points

* LLM API for keyword/description generation (configurable endpoint)

* Embedding API (to be provided)

* Chrome extension APIs (tabs, storage, new tab override)

### Data Storage & Privacy

* All data stored locally on user’s machine (no cloud sync)

* User controls for exclusion, deletion, and export/import

* No PII sent to external APIs (content only, never user identity)

* Compliance with Chrome Web Store privacy requirements

### Scalability & Performance

* Designed for <1000 documents per user

* Fast search and indexing for small datasets

* Minimal resource usage to avoid browser slowdowns

### Potential Challenges

* Ensuring robust content extraction across diverse web pages

* Handling dynamic URLs and query strings as unique entries

* Managing local storage limits and performance

* Providing a seamless user experience with minimal permissions

---

## Milestones & Sequencing

### Project Estimate

* Small: 1–2 weeks

### Team Size & Composition

* Small Team: 1–2 total people

  * 1 Full-stack Engineer (extension + backend)

  * 1 Product/Design (can be part-time or shared)
