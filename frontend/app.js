// Zod is loaded via CDN as the global `Zod` object (UMD build)
const z = Zod.z || Zod;

// ── Constants ─────────────────────────────────────────────────────────────────

const PROVIDERS = ['anthropic', 'openai', 'ollama'];

const MODELS = {
  anthropic: ['claude-haiku-4-5', 'claude-sonnet-4-5'],
  openai: ['gpt-4.1', 'gpt-5.2'],
  ollama: ['gemma3:4b', 'deepseek-r1:1.5b'],
};

const SYSTEM_PROMPTS = {
  en: {
    prompt1: `You are a compliance analyst specialising in information security standards.

Given a security control requirement and a policy document, determine whether the policy document satisfies the control.

Respond ONLY with valid JSON in this exact format:
{
  "match": "yes" | "no" | "partial",
  "if_yes_reason": "Brief explanation if match is yes or partial, otherwise empty string",
  "suggestions": "Specific, actionable suggestions to achieve compliance if match is no or partial. Empty string if full match."
}`,
    prompt2: `You are a policy improvement specialist. You receive a security control requirement and raw improvement suggestions.

Rewrite the suggestions into clear, concise, and actionable policy recommendations.

Respond ONLY with valid JSON in this exact format:
{
  "rewritten_suggestions": ["Actionable recommendation 1", "Actionable recommendation 2", "Actionable recommendation 3"]
}`,
  },
  nl: {
    prompt1: `Je bent een compliance-analist gespecialiseerd in informatiebeveiligingsnormen.

Gegeven een beveiligingscontrolevereiste en een beleidsdocument, bepaal of het beleidsdocument voldoet aan de controle.

Reageer ALLEEN met geldige JSON in dit exacte formaat:
{
  "match": "yes" | "no" | "partial",
  "if_yes_reason": "Korte uitleg als de match yes of partial is, anders lege string",
  "suggestions": "Specifieke, uitvoerbare suggesties om naleving te bereiken als de match no of partial is. Lege string bij volledige match."
}`,
    prompt2: `Je bent een beleidsverbeteringsspecialist. Je ontvangt een beveiligingscontrolevereiste en ruwe verbeteringssuggesties.

Herschrijf de suggesties tot duidelijke, beknopte en uitvoerbare beleidsaanbevelingen.

Reageer ALLEEN met geldige JSON in dit exacte formaat:
{
  "rewritten_suggestions": ["Uitvoerbare aanbeveling 1", "Uitvoerbare aanbeveling 2", "Uitvoerbare aanbeveling 3"]
}`,
  },
};

// ── Zod schemas ───────────────────────────────────────────────────────────────

const analysisFormSchema = z.object({
  client_name: z.string().min(1, 'Client name is required'),
  system_prompt1: z.string().min(1, 'System prompt cannot be empty'),
  selected_provider1: z.enum(PROVIDERS, { message: 'Invalid provider' }),
  selected_llm1: z.string().min(1, 'Model must be selected'),
});

const rewriteFormSchema = z.object({
  system_prompt2: z.string().min(1, 'System prompt cannot be empty'),
  selected_provider2: z.enum(PROVIDERS, { message: 'Invalid provider' }),
  selected_llm2: z.string().min(1, 'Model must be selected'),
  input_xlsx_filename: z.string().min(1, 'No output from Analysis found — run Step 2 first'),
});

const analysisResultItemSchema = z.object({
  id: z.union([z.string(), z.number()]),
  match: z.enum(['yes', 'no', 'partial']),
  if_yes_reason: z.string(),
  suggestions: z.string(),
});

const analysisResponseSchema = z.object({
  json_file: z.string(),
  xlsx_file: z.string(),
  results: z.array(analysisResultItemSchema),
});

const rewriteResultItemSchema = z.object({
  id: z.union([z.string(), z.number()]),
  rewritten_suggestions: z.array(z.string()),
});

const rewriteResponseSchema = z.object({
  json_file: z.string(),
  xlsx_file: z.string(),
  results: z.array(rewriteResultItemSchema),
});

const reportFormSchema = z.object({
  input_xlsx_filename: z.string().min(1, 'No output from Rewrite found — run Step 2 first'),
});

// ── App state ─────────────────────────────────────────────────────────────────

let analysisXlsxFile = null;
let rewriteXlsxFile = null;

// ── UI helpers ────────────────────────────────────────────────────────────────

function showStatus(id, type, html) {
  const el = document.getElementById(id);
  el.className = `status ${type}`;
  el.style.display = 'block';
  el.innerHTML = html;
}

function hideStatus(id) {
  document.getElementById(id).style.display = 'none';
}

function setBtn(id, disabled, label) {
  const btn = document.getElementById(id);
  btn.disabled = disabled;
  if (label !== undefined) btn.textContent = label;
}

// ── Initialisation helpers ────────────────────────────────────────────────────

function updateModels(section) {
  const provider = document.getElementById(`provider${section}`).value;
  const sel = document.getElementById(`model${section}`);
  sel.innerHTML = (MODELS[provider] || [])
    .map(m => `<option value="${m}">${m}</option>`)
    .join('');
}

function onLanguageChange() {
  const lang = document.getElementById('language').value;
  const prompts = SYSTEM_PROMPTS[lang] || SYSTEM_PROMPTS.en;
  document.getElementById('system_prompt1').value = prompts.prompt1;
  document.getElementById('system_prompt2').value = prompts.prompt2;
}

// ── Analysis ──────────────────────────────────────────────────────────────────

async function runAnalysis() {
  const xlsxFile = document.getElementById('xlsx_file').files[0];
  const pdfFile = document.getElementById('pdf_file').files[0];

  // File presence checks (File objects cannot be validated by Zod)
  if (!xlsxFile) return showStatus('status1', 'error', 'Please upload a standard .xlsx file.');
  if (!pdfFile) return showStatus('status1', 'error', 'Please upload a client document (.pdf).');

  // Zod validation for text fields
  const parse = analysisFormSchema.safeParse({
    client_name: document.getElementById('client_name').value.trim(),
    system_prompt1: document.getElementById('system_prompt1').value.trim(),
    selected_provider1: document.getElementById('provider1').value,
    selected_llm1: document.getElementById('model1').value,
  });

  if (!parse.success) {
    const msg = parse.error.errors.map(e => e.message).join('<br/>');
    return showStatus('status1', 'error', msg);
  }

  const { client_name, system_prompt1, selected_provider1, selected_llm1 } = parse.data;

  showStatus('status1', 'loading', '⏳ Analysing policy document&hellip; this may take a few minutes.');
  setBtn('btn1', true, 'Processing…');

  const form = new FormData();
  form.append('pdf_file', pdfFile);
  form.append('xlsx_file', xlsxFile);
  form.append('client_name', client_name);
  form.append('system_prompt1', system_prompt1);
  form.append('selected_provider1', selected_provider1);
  form.append('selected_llm1', selected_llm1);

  try {
    const resp = await fetch('/api/process/analyze', { method: 'POST', body: form });
    if (!resp.ok) {
      let detail = `HTTP ${resp.status}`;
      try { detail = (await resp.json()).detail || detail; } catch { }
      throw new Error(detail);
    }
    const raw = await resp.json();

    // Validate API response shape
    const responseParseResult = analysisResponseSchema.safeParse(raw);
    if (!responseParseResult.success) {
      const errs = responseParseResult.error.errors.map(e => `${e.path.join('.')}: ${e.message}`).join('; ');
      throw new Error(`Unexpected response shape — ${errs}`);
    }

    const data = responseParseResult.data;
    analysisXlsxFile = data.xlsx_file;
    setBtn('btn2', false);

    const rows = data.results;
    const tableRows = rows.map(r => `
      <tr>
        <td>${escHtml(String(r.id))}</td>
        <td><span class="badge badge-${r.match}">${r.match}</span></td>
        <td>${escHtml(r.if_yes_reason)}</td>
        <td>${escHtml(r.suggestions)}</td>
      </tr>
    `).join('');

    showStatus('status1', 'success', `
      <strong>Done!</strong> Output saved as <code>${escHtml(data.xlsx_file)}</code>
      <div class="table-wrap">
        <table class="result-table">
          <thead>
            <tr><th>ID</th><th>Match</th><th>Reason</th><th>Suggestions</th></tr>
          </thead>
          <tbody>${tableRows}</tbody>
        </table>
      </div>
    `);
  } catch (err) {
    showStatus('status1', 'error', `<strong>Error:</strong> ${escHtml(err.message)}`);
  } finally {
    setBtn('btn1', false, 'Run Analysis');
  }
}

// ── Rewrite ──────────────────────────────────────────────────────────────────

async function runRewrite() {
  const parse = rewriteFormSchema.safeParse({
    system_prompt2: document.getElementById('system_prompt2').value.trim(),
    selected_provider2: document.getElementById('provider2').value,
    selected_llm2: document.getElementById('model2').value,
    input_xlsx_filename: analysisXlsxFile || '',
  });

  if (!parse.success) {
    const msg = parse.error.errors.map(e => e.message).join('<br/>');
    return showStatus('status2', 'error', msg);
  }

  const { system_prompt2, selected_provider2, selected_llm2, input_xlsx_filename } = parse.data;

  showStatus('status2', 'loading', '⏳ Rewriting suggestions&hellip; this may take a few minutes.');
  setBtn('btn2', true, 'Processing…');

  const form = new FormData();
  form.append('input_xlsx_filename', input_xlsx_filename);
  form.append('system_prompt2', system_prompt2);
  form.append('selected_provider2', selected_provider2);
  form.append('selected_llm2', selected_llm2);

  try {
    const resp = await fetch('/api/process/rewrite', { method: 'POST', body: form });
    if (!resp.ok) {
      let detail = `HTTP ${resp.status}`;
      try { detail = (await resp.json()).detail || detail; } catch { }
      throw new Error(detail);
    }
    const raw = await resp.json();

    const responseParseResult = rewriteResponseSchema.safeParse(raw);
    if (!responseParseResult.success) {
      const errs = responseParseResult.error.errors.map(e => `${e.path.join('.')}: ${e.message}`).join('; ');
      throw new Error(`Unexpected response shape — ${errs}`);
    }

    const data = responseParseResult.data;
    rewriteXlsxFile = data.xlsx_file;
    setBtn('btn3', false);

    const rows = data.results;
    const tableRows = rows.map(r => {
      const items = r.rewritten_suggestions
        .map(s => `<li>${escHtml(s)}</li>`)
        .join('');
      return `
        <tr>
          <td>${escHtml(String(r.id))}</td>
          <td><ul style="margin:0;padding-left:1.2rem;line-height:1.6">${items}</ul></td>
        </tr>
      `;
    }).join('');

    showStatus('status2', 'success', `
      <strong>Done!</strong> Output saved as <code>${escHtml(data.xlsx_file)}</code>
      <div class="table-wrap">
        <table class="result-table">
          <thead>
            <tr><th>ID</th><th>Rewritten Suggestions</th></tr>
          </thead>
          <tbody>${tableRows}</tbody>
        </table>
      </div>
    `);
  } catch (err) {
    showStatus('status2', 'error', `<strong>Error:</strong> ${escHtml(err.message)}`);
  } finally {
    setBtn('btn2', false, 'Rewrite Suggestions');
  }
}

// ── Report ──────────────────────────────────────────────────────────────────

async function runReport() {
  const parse = reportFormSchema.safeParse({
    input_xlsx_filename: rewriteXlsxFile || '',
  });

  if (!parse.success) {
    const msg = parse.error.errors.map(e => e.message).join('<br/>');
    return showStatus('status3', 'error', msg);
  }

  const { input_xlsx_filename } = parse.data;

  showStatus('status3', 'loading', '⏳ Generating report&hellip;');
  setBtn('btn3', true, 'Processing…');

  const form = new FormData();
  form.append('input_xlsx_filename', input_xlsx_filename);

  try {
    const resp = await fetch('/api/process/report', { method: 'POST', body: form });
    if (!resp.ok) {
      let detail = `HTTP ${resp.status}`;
      try { detail = (await resp.json()).detail || detail; } catch { }
      throw new Error(detail);
    }
    const raw = await resp.json();

    const docxFile = raw.docx_file ? ` — <code>${escHtml(raw.docx_file)}</code>` : '';
    const downloadHtml = raw.docx_file
      ? `<br/><br/><a href="/api/download/${encodeURIComponent(raw.docx_file)}" class="btn btn-success" target="_blank">Download Report</a>`
      : '';
    showStatus('status3', 'success', `<strong>Report generated!</strong>${docxFile}${downloadHtml}`);
  } catch (err) {
    showStatus('status3', 'error', `<strong>Error:</strong> ${escHtml(err.message)}`);
  } finally {
    setBtn('btn3', false, 'Generate Report');
  }
}

// ── Security helper ───────────────────────────────────────────────────────────

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Bootstrap ─────────────────────────────────────────────────────────────────

updateModels(1);
updateModels(2);
onLanguageChange();
