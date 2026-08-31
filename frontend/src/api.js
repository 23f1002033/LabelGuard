export async function fetchJurisdictions() {
  const res = await fetch('/api/jurisdictions')
  if (!res.ok) throw new Error('Could not load jurisdictions')
  return res.json()
}

export async function analyzeLabel({ file, jurisdiction, system, imported, singleIngredient }) {
  const form = new FormData()
  form.append('image', file)
  form.append('jurisdiction', jurisdiction)
  form.append('system', system)
  if (imported !== null) form.append('imported', String(imported))
  if (singleIngredient !== null) form.append('single_ingredient', String(singleIngredient))

  const res = await fetch('/api/analyze', { method: 'POST', body: form })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed with status ${res.status}`)
  }
  return res.json()
}
