import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  ArrowRight,
  Check,
  CheckCircle2,
  Clock3,
  FileSpreadsheet,
  Link2,
  ListPlus,
  LoaderCircle,
  Minus,
  Play,
  ScrollText,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { getJob, submitJob } from "./api";

const TERMINAL_STATUSES = new Set(["completed", "failed"]);
const MAX_LINKS = 100;
const SAVED_LINKS_KEY = "retail-banking.telegram-links";

function formatLocalInput(date) {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

function initialDates() {
  const end = new Date();
  const start = new Date(end.getTime() - 24 * 60 * 60 * 1000);
  return { start: formatLocalInput(start), end: formatLocalInput(end) };
}

function initialLinks() {
  try {
    const saved = JSON.parse(window.localStorage.getItem(SAVED_LINKS_KEY) || "[]");
    const links = Array.isArray(saved)
      ? saved.map((link) => String(link || "")).slice(0, MAX_LINKS)
      : [];
    return links.length ? links : [""];
  } catch {
    return [""];
  }
}

function validateForm(links, startDate, endDate) {
  const activeLinks = links.map((link) => link.trim()).filter(Boolean);
  if (!activeLinks.length) return "Add at least one Telegram channel or group link.";
  const invalid = activeLinks.find(
    (link) => !/^https:\/\/(?:www\.)?(?:t\.me|telegram\.me)\/[^\s/]+\/?$/i.test(link),
  );
  if (invalid) return `Check this Telegram link: ${invalid}`;
  if (!startDate || !endDate) return "Choose both a start and end date.";
  if (new Date(startDate) >= new Date(endDate)) {
    return "The start date must be earlier than the end date.";
  }
  return "";
}

function StatusPill({ status }) {
  const label = status ? status[0].toUpperCase() + status.slice(1) : "Ready";
  return <span className={`status-pill status-${status || "ready"}`}>{label}</span>;
}

function App() {
  const defaults = useMemo(initialDates, []);
  const [links, setLinks] = useState(initialLinks);
  const [startDate, setStartDate] = useState(defaults.start);
  const [endDate, setEndDate] = useState(defaults.end);
  const [job, setJob] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");
  const [notice, setNotice] = useState(null);
  const isActive = submitting || ["queued", "running"].includes(job?.status);

  useEffect(() => {
    window.localStorage.setItem(SAVED_LINKS_KEY, JSON.stringify(links));
  }, [links]);

  useEffect(() => {
    if (!job?.id || TERMINAL_STATUSES.has(job.status)) return undefined;

    const poll = window.setInterval(async () => {
      try {
        const updated = await getJob(job.id);
        setJob(updated);
        if (updated.status === "completed") {
          setNotice({ type: "success", text: "Google Sheets has been updated successfully." });
        } else if (updated.status === "failed") {
          setNotice({ type: "error", text: updated.error || "The scraping job failed." });
        }
      } catch (error) {
        setNotice({ type: "error", text: error.message });
      }
    }, 1500);

    return () => window.clearInterval(poll);
  }, [job?.id, job?.status]);

  function updateLink(index, value) {
    setLinks((current) => current.map((link, item) => (item === index ? value : link)));
  }

  function removeLink(index) {
    setLinks((current) =>
      current.length === 1 ? [""] : current.filter((_, item) => item !== index),
    );
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const error = validateForm(links, startDate, endDate);
    setFormError(error);
    setNotice(null);
    if (error) return;

    setSubmitting(true);
    try {
      const created = await submitJob({
        links: links.map((link) => link.trim()).filter(Boolean),
        start_date: new Date(startDate).toISOString(),
        end_date: new Date(endDate).toISOString(),
      });
      setJob(created);
      setNotice({ type: "info", text: "Your scraping job has been added to the queue." });
    } catch (submitError) {
      setNotice({ type: "error", text: submitError.message });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main>
      <header className="hero">
        <nav className="topbar" aria-label="Primary navigation">
          <div className="brand">
            <span className="brand-mark" aria-hidden="true">CM</span>
            <span><strong>CHIP MONG</strong><small>RETAIL BANKING</small></span>
          </div>
          <div className="secure-label"><ShieldCheck size={17} /> Secure internal portal</div>
        </nav>

        <div className="hero-copy">
          <span className="eyebrow"><Sparkles size={15} /> Modern Scraping Portal</span>
          <h1>Retail Call Plan</h1> 
          <p>
            Choose your reporting window, add Telegram sources, and let the portal
            securely deliver structured records to Google Sheets.
          </p>
        </div>
        <div className="hero-orb hero-orb-one" />
        <div className="hero-orb hero-orb-two" />
      </header>

      <section className="form-shell" aria-labelledby="scrape-form-title">
        <div className="section-heading">
          <div>
            <span className="section-kicker">NEW SCRAPING RUN</span>
            <h2 id="scrape-form-title">Set up your data request</h2>
          </div>
          <span className="timezone"><Clock3 size={16} /> Cambodia time (UTC+7)</span>
        </div>

        <form onSubmit={handleSubmit} noValidate>
          <div className="date-grid">
            <label>
              <span>Start date &amp; time</span>
              <input
                type="datetime-local"
                value={startDate}
                onChange={(event) => setStartDate(event.target.value)}
                disabled={isActive}
              />
            </label>
            <label>
              <span>End date &amp; time</span>
              <input
                type="datetime-local"
                value={endDate}
                onChange={(event) => setEndDate(event.target.value)}
                disabled={isActive}
              />
            </label>
          </div>

          <div className="links-heading">
            <div><Link2 size={18} /><span>Telegram sources</span></div>
            <span>{links.length} of {MAX_LINKS} links</span>
          </div>
          <div className="link-list">
            {links.map((link, index) => (
              <div className="link-row" key={index}>
                <span className="link-number">{String(index + 1).padStart(2, "0")}</span>
                <input
                  type="url"
                  aria-label={`Telegram link ${index + 1}`}
                  placeholder="https://t.me/channel_or_group"
                  value={link}
                  onChange={(event) => updateLink(index, event.target.value)}
                  disabled={isActive}
                />
                <button
                  className="icon-button"
                  type="button"
                  aria-label={`Remove Telegram link ${index + 1}`}
                  onClick={() => removeLink(index)}
                  disabled={isActive}
                >
                  <Minus size={17} />
                </button>
              </div>
            ))}
          </div>

          <div className="form-actions">
            <button
              className="add-link"
              type="button"
              onClick={() => setLinks((current) => [...current, ""])}
              disabled={isActive || links.length >= MAX_LINKS}
            >
              <ListPlus size={17} /> Add another link
            </button>
            <button className="run-button" type="submit" disabled={isActive}>
              {isActive ? <LoaderCircle className="spin" size={19} /> : <Play size={18} />}
              {isActive ? "Scraping in progress" : "Run scraping"}
              {!isActive && <ArrowRight size={18} />}
            </button>
          </div>
          {formError && <p className="field-error"><AlertCircle size={16} /> {formError}</p>}
        </form>
      </section>

      {notice && (
        <div className={`notice notice-${notice.type}`} role="status">
          {notice.type === "success" ? <CheckCircle2 size={20} /> : notice.type === "error" ? <AlertCircle size={20} /> : <Clock3 size={20} />}
          <span>{notice.text}</span>
          <button type="button" onClick={() => setNotice(null)} aria-label="Dismiss notification">×</button>
        </div>
      )}

      <section className="dashboard-grid" aria-live="polite">
        <article className="card result-card">
          <div className="card-title-row">
            <div>
              <span className="section-kicker">LIVE EXECUTION</span>
              <h2>Scraping status</h2>
            </div>
            <StatusPill status={job?.status} />
          </div>

          {!job ? (
            <div className="empty-state">
              <span className="empty-icon"><FileSpreadsheet size={27} /></span>
              <h3>Ready for your first run</h3>
              <p>Complete the form above to start collecting Retail Banking records.</p>
            </div>
          ) : (
            <div className="job-content">
              <div className="progress-copy">
                <span>{job.status_message}</span><strong>{job.progress}%</strong>
              </div>
              <div className="progress-track"><span style={{ width: `${job.progress}%` }} /></div>
              <div className="stat-grid">
                <div><span>Sources</span><strong>{job.links.length}</strong></div>
                <div><span>Records found</span><strong>{job.records_found}</strong></div>
                <div><span>Rows added</span><strong>{job.rows_appended}</strong></div>
                <div><span>Duplicates</span><strong>{job.duplicates_skipped}</strong></div>
              </div>
              {job.error && <div className="job-error"><AlertCircle size={18} /> {job.error}</div>}
            </div>
          )}
        </article>

        <aside className="card process-card">
          <span className="section-kicker">HOW IT WORKS</span>
          <h2>Three simple steps</h2>
          <ol className="steps">
            <li><span>1</span><div><strong>Choose a date range</strong><small>Select the exact reporting window.</small></div></li>
            <li><span>2</span><div><strong>Add Telegram links</strong><small>Include every source you need.</small></div></li>
            <li><span>3</span><div><strong>Run and review</strong><small>Results flow into Google Sheets.</small></div></li>
          </ol>
          <div className="security-note"><ShieldCheck size={19} /><span><strong>One secure account</strong><small>Telegram credentials stay on the server.</small></span></div>
        </aside>

        {job?.logs?.length > 0 && (
          <article className="card logs-card">
            <div className="card-title-row">
              <div><span className="section-kicker">ACTIVITY</span><h2>Execution log</h2></div>
              <ScrollText size={21} />
            </div>
            <div className="log-list">
              {job.logs.map((log, index) => (
                <div className={`log-row log-${log.level}`} key={`${log.timestamp}-${index}`}>
                  <span>{log.level === "success" ? <Check size={14} /> : <span className="log-dot" />}</span>
                  <time>{new Date(log.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</time>
                  <p>{log.message}</p>
                </div>
              ))}
            </div>
          </article>
        )}
      </section>

      <footer><span>CHIP MONG RETAIL</span><span>Retail Banking Data Portal · Internal Use</span></footer>
    </main>
  );
}

export default App;
