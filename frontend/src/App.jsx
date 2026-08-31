import { useEffect, useState } from 'react'
import { analyzeLabel, fetchJurisdictions } from './api.js'

const TRACE_LABELS = {
  load_rule_pack: 'Loaded rule pack',
  ocr_extract: 'Extracted text (OCR)',
  single_llm_call: 'Generated report in a single pass',
  report_generated: 'Generated final report',
  generate_final_report: 'Generated final report',
  extract_label_fields: 'Extracted label fields',
  select_applicable_rules: 'Selected applicable rules',
  generate_candidate_findings: 'Generated candidate findings',
  verify_findings: 'Verified findings',
}

function StatusBadge({ status }) {
  return <span className={`badge badge-${status.toLowerCase().replace('_', '-')}`}>{status.replace('_', ' ')}</span>
}

function SeverityBadge({ severity }) {
  return <span className={`sev sev-${severity}`}>{severity}</span>
}

function TraceTimeline({ events, system }) {
  return (
    <div className="trace-panel">
      <h3>Agent trace</h3>
      <p className="trace-sub">
        {system === 'agent'
          ? 'Four specialised steps ran for this analysis.'
          : 'The baseline ran OCR plus a single model call, with no retrieval or verification step.'}
      </p>
      <ol className="trace-list">
        {events.map((e, i) => (
          <li key={i} className="trace-item">
            <span className="trace-dot" />
            <div>
              <div className="trace-title">{TRACE_LABELS[e.step] || e.step}</div>
              <div className="trace-result">{e.result}</div>
            </div>
          </li>
        ))}
      </ol>
    </div>
  )
}

function EvidenceList({ evidence }) {
  if (!evidence || evidence.length === 0) return null
  return (
    <div className="evidence">
      {evidence.map((ev, i) => (
        <div key={i} className="evidence-item">
          <span className="evidence-kind">{ev.kind.replace('_', ' ')}</span>
          {ev.snippet && <span className="evidence-snippet">"{ev.snippet}"</span>}
        </div>
      ))}
    </div>
  )
}

function FindingCard({ finding }) {
  return (
    <div className={`finding finding-${finding.status.toLowerCase().replace('_', '-')}`}>
      <div className="finding-head">
        <StatusBadge status={finding.status} />
        <SeverityBadge severity={finding.severity} />
        <span className="finding-rule-id">{finding.rule_id}</span>
      </div>
      <div className="finding-requirement">{finding.requirement}</div>
      <div className="finding-explanation">{finding.explanation}</div>
      <EvidenceList evidence={finding.evidence} />
      {finding.suggested_fix && (
        <div className="finding-fix"><strong>Suggested fix:</strong> {finding.suggested_fix}</div>
      )}
      {finding.verification && (
        <div className="finding-verification">
          <strong>Verifier:</strong> {finding.verification.verdict} - {finding.verification.reason}
        </div>
      )}
      <div className="finding-meta">
        <span>confidence {(finding.confidence * 100).toFixed(0)}%</span>
        {finding.source_name && (
          <a href={finding.source_url} target="_blank" rel="noreferrer">{finding.source_name}</a>
        )}
      </div>
    </div>
  )
}

function FindingSection({ title, findings, defaultOpen }) {
  const [open, setOpen] = useState(defaultOpen)
  if (findings.length === 0) return null
  return (
    <div className="finding-section">
      <button className="section-toggle" onClick={() => setOpen(!open)}>
        {open ? '-' : '+'} {title} ({findings.length})
      </button>
      {open && <div className="finding-list">{findings.map((f) => <FindingCard key={f.finding_id} finding={f} />)}</div>}
    </div>
  )
}

function ReportView({ report }) {
  const failed = report.findings.filter((f) => f.status === 'FAIL')
  const review = report.findings.filter((f) => f.status === 'NEEDS_REVIEW')
  const passed = report.findings.filter((f) => f.status === 'PASS')
  const na = report.findings.filter((f) => f.status === 'NOT_APPLICABLE')

  return (
    <div className="report">
      <div className="report-header">
        <div>
          <h2>{report.product_name || 'Unnamed product'}</h2>
          <p className="report-sub">{report.jurisdiction_name} &middot; {report.product_category.replace('_', ' ')}</p>
        </div>
        <div className={`overall overall-${report.overall_status.toLowerCase().replace('_', '-')}`}>
          {report.overall_status.replace('_', ' ')}
        </div>
      </div>

      <div className="summary-grid">
        <div><span className="summary-num">{report.summary.passed}</span>Passed</div>
        <div><span className="summary-num">{report.summary.failed}</span>Failed</div>
        <div><span className="summary-num">{report.summary.needs_review}</span>Needs review</div>
        <div><span className="summary-num">{report.summary.not_applicable}</span>Not applicable</div>
        <div><span className="summary-num">{report.summary.compliance_score}%</span>Compliance score</div>
      </div>

      <FindingSection title="Critical / High Risk Findings" findings={failed} defaultOpen={true} />
      <FindingSection title="Needs Review" findings={review} defaultOpen={true} />
      <FindingSection title="Passed Requirements" findings={passed} defaultOpen={false} />
      <FindingSection title="Not Applicable" findings={na} defaultOpen={false} />

      <div className="sources">
        <h3>Sources</h3>
        <ul>
          {report.sources.map((s) => (
            <li key={s.source_id}><a href={s.url} target="_blank" rel="noreferrer">{s.name}</a></li>
          ))}
        </ul>
      </div>

      <div className="disclaimer">{report.disclaimer}</div>

      {(report.runtime_seconds || report.token_usage?.total_tokens) && (
        <div className="run-meta">
          {report.runtime_seconds && <span>runtime {report.runtime_seconds.toFixed(1)}s</span>}
          {report.token_usage?.total_tokens > 0 && <span>{report.token_usage.total_tokens} tokens</span>}
        </div>
      )}
    </div>
  )
}

export default function App() {
  const [jurisdictions, setJurisdictions] = useState([])
  const [jurisdiction, setJurisdiction] = useState('IN')
  const [system, setSystem] = useState('agent')
  const [imported, setImported] = useState(null)
  const [singleIngredient, setSingleIngredient] = useState(null)
  const [file, setFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState(null)
  const [status, setStatus] = useState('setup')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchJurisdictions().then(setJurisdictions).catch(() => setError('Could not reach the LabelGuard API'))
  }, [])

  function handleFile(e) {
    const f = e.target.files[0]
    if (!f) return
    setFile(f)
    setPreviewUrl(URL.createObjectURL(f))
  }

  async function handleAnalyze() {
    if (!file) {
      setError('Choose a label image first')
      return
    }
    setError(null)
    setStatus('analyzing')
    try {
      const data = await analyzeLabel({ file, jurisdiction, system, imported, singleIngredient })
      setResult(data)
      setStatus('report')
    } catch (err) {
      setError(err.message)
      setStatus('setup')
    }
  }

  function handleReset() {
    setStatus('setup')
    setResult(null)
    setFile(null)
    setPreviewUrl(null)
    setError(null)
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>LabelGuard</h1>
        <p>AI-powered global product label compliance auditing with evidence-backed verification.</p>
      </header>

      {status !== 'report' && (
        <div className="setup-card">
          <div className="field-row">
            <label>
              1. Upload product label
              <input type="file" accept="image/png,image/jpeg,image/webp" onChange={handleFile} />
            </label>
            {previewUrl && <img className="preview" src={previewUrl} alt="Label preview" />}
          </div>

          <div className="field-row">
            <label>
              2. Target jurisdiction
              <select value={jurisdiction} onChange={(e) => setJurisdiction(e.target.value)}>
                {jurisdictions.map((j) => (
                  <option key={j.code} value={j.code}>{j.name} ({j.rule_count} requirements)</option>
                ))}
              </select>
            </label>
            <label>
              3. Product category
              <select disabled value="packaged_food">
                <option value="packaged_food">Packaged food</option>
              </select>
            </label>
          </div>

          <div className="field-row">
            <label>
              Imported product?
              <select value={imported === null ? '' : String(imported)} onChange={(e) => setImported(e.target.value === '' ? null : e.target.value === 'true')}>
                <option value="">Not specified</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            </label>
            <label>
              Single ingredient?
              <select value={singleIngredient === null ? '' : String(singleIngredient)} onChange={(e) => setSingleIngredient(e.target.value === '' ? null : e.target.value === 'true')}>
                <option value="">Not specified</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            </label>
            <label>
              System
              <select value={system} onChange={(e) => setSystem(e.target.value)}>
                <option value="agent">Agent (extraction, retrieval, compliance, verification)</option>
                <option value="baseline">Baseline (OCR + single model call)</option>
              </select>
            </label>
          </div>

          {error && <div className="error-box">{error}</div>}

          <button className="analyze-btn" onClick={handleAnalyze} disabled={status === 'analyzing'}>
            {status === 'analyzing' ? 'Analyzing...' : '4. Analyze'}
          </button>
        </div>
      )}

      {status === 'analyzing' && (
        <div className="analyzing-box">
          <div className="spinner" />
          <p>Running {system === 'agent' ? 'the 4-agent pipeline' : 'the baseline system'}...</p>
        </div>
      )}

      {status === 'report' && result && (
        <div className="results-layout">
          <div className="results-main">
            <ReportView report={result.report} />
          </div>
          <div className="results-side">
            <TraceTimeline events={result.trace} system={result.report.system} />
            <button className="reset-btn" onClick={handleReset}>Analyze another label</button>
          </div>
        </div>
      )}
    </div>
  )
}
