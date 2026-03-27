import jsPDF from 'jspdf'

// ── Helpers ──────────────────────────────────────────────────────────────────

const BRAND_COLOR: [number, number, number] = [99, 102, 241]   // indigo-500
const TEXT_DARK:   [number, number, number] = [15,  23,  42]   // slate-950
const TEXT_MID:    [number, number, number] = [100, 116, 139]  // slate-500
const TEXT_LIGHT:  [number, number, number] = [226, 232, 240]  // slate-200
const BG_CARD:     [number, number, number] = [30,  41,  59]   // slate-800

function addHeader(doc: jsPDF, title: string, subtitle: string) {
  // Brand bar
  doc.setFillColor(...BRAND_COLOR)
  doc.rect(0, 0, 210, 18, 'F')

  doc.setFontSize(11)
  doc.setTextColor(255, 255, 255)
  doc.setFont('helvetica', 'bold')
  doc.text('Data Dictionary Agent', 10, 11)

  doc.setFontSize(9)
  doc.setFont('helvetica', 'normal')
  doc.text(new Date().toLocaleDateString('en-IN', { dateStyle: 'medium' }), 200, 11, { align: 'right' })

  // Page title
  doc.setFontSize(18)
  doc.setFont('helvetica', 'bold')
  doc.setTextColor(...TEXT_DARK)
  doc.text(title, 10, 32)

  doc.setFontSize(10)
  doc.setFont('helvetica', 'normal')
  doc.setTextColor(...TEXT_MID)
  doc.text(subtitle, 10, 39)

  return 48  // y cursor after header
}

function addSectionHeading(doc: jsPDF, label: string, y: number): number {
  doc.setFillColor(...BRAND_COLOR)
  doc.rect(10, y, 2, 6, 'F')
  doc.setFontSize(10)
  doc.setFont('helvetica', 'bold')
  doc.setTextColor(...TEXT_DARK)
  doc.text(label, 15, y + 5)
  return y + 12
}

function addWrappedText(doc: jsPDF, text: string, x: number, y: number, maxWidth: number, lineHeight = 5): number {
  doc.setFontSize(9)
  doc.setFont('helvetica', 'normal')
  doc.setTextColor(...TEXT_DARK)
  const lines = doc.splitTextToSize(text, maxWidth)
  doc.text(lines, x, y)
  return y + lines.length * lineHeight
}

function checkPage(doc: jsPDF, y: number, margin = 270): number {
  if (y > margin) {
    doc.addPage()
    return 20
  }
  return y
}

// ── Export: Data Dictionary ───────────────────────────────────────────────────

export interface DictExportData {
  connectionId: string
  tables: Array<{
    name: string
    row_count?: number
    columns: Array<{ name: string; type: string; primary_key?: boolean; foreign_keys?: unknown[] }>
    doc?: {
      business_summary?: string
      purpose?: string
      table_type?: string
      key_questions?: string[]
      recommended_joins?: string[]
    }
    quality?: {
      quality_score: number
      total_rows?: number
    }
  }>
}

export function exportDictionaryPDF(data: DictExportData) {
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' })
  let y = addHeader(doc, 'Data Dictionary', `Connection: ${data.connectionId}`)

  doc.setFontSize(9)
  doc.setTextColor(...TEXT_MID)
  doc.text(`${data.tables.length} tables documented`, 10, y)
  y += 10

  for (const table of data.tables) {
    y = checkPage(doc, y)

    // Table title bar
    doc.setFillColor(...BG_CARD)
    doc.roundedRect(10, y, 190, 10, 2, 2, 'F')
    doc.setFontSize(11)
    doc.setFont('helvetica', 'bold')
    doc.setTextColor(...TEXT_LIGHT)
    doc.text(table.name, 14, y + 6.5)

    if (table.quality) {
      const score = Math.round(table.quality.quality_score)
      const color: [number, number, number] = score >= 90 ? [16, 185, 129] : score >= 70 ? [245, 158, 11] : [239, 68, 68]
      doc.setFontSize(9)
      doc.setFont('helvetica', 'bold')
      doc.setTextColor(...color)
      doc.text(`Quality ${score}%`, 190, y + 6.5, { align: 'right' })
    }
    y += 14

    // Business summary
    if (table.doc?.business_summary) {
      y = addWrappedText(doc, table.doc.business_summary, 12, y, 186)
      y += 3
    }

    // Purpose
    if (table.doc?.purpose) {
      doc.setFontSize(8)
      doc.setTextColor(...TEXT_MID)
      const lines = doc.splitTextToSize(table.doc.purpose, 186)
      doc.text(lines, 12, y)
      y += lines.length * 4.5 + 3
    }

    // Key questions
    if (table.doc?.key_questions?.length) {
      doc.setFontSize(8)
      doc.setFont('helvetica', 'bold')
      doc.setTextColor(...TEXT_MID)
      doc.text('Key Questions:', 12, y); y += 5
      doc.setFont('helvetica', 'normal')
      for (const q of table.doc.key_questions) {
        y = checkPage(doc, y)
        doc.setTextColor(99, 102, 241)
        doc.text('?', 13, y)
        doc.setTextColor(...TEXT_DARK)
        const lines = doc.splitTextToSize(q, 182)
        doc.text(lines, 17, y)
        y += lines.length * 4.5
      }
      y += 3
    }

    // Columns table header
    y = checkPage(doc, y)
    doc.setFillColor(241, 245, 249)
    doc.rect(12, y, 186, 6, 'F')
    doc.setFontSize(7.5)
    doc.setFont('helvetica', 'bold')
    doc.setTextColor(71, 85, 105)
    doc.text('Column', 14, y + 4)
    doc.text('Type', 70, y + 4)
    doc.text('Nullable', 130, y + 4)
    doc.text('Flags', 165, y + 4)
    y += 7

    for (const col of table.columns) {
      y = checkPage(doc, y)
      doc.setFontSize(7.5)
      doc.setFont('helvetica', 'normal')
      doc.setTextColor(...TEXT_DARK)
      doc.text(col.name, 14, y)
      doc.setTextColor(...TEXT_MID)
      doc.text(col.type, 70, y)
      doc.text(col.primary_key ? 'NO' : 'yes', 130, y)

      const flags: string[] = []
      if (col.primary_key) flags.push('PK')
      if ((col.foreign_keys as unknown[])?.length) flags.push('FK')
      if (flags.length) {
        doc.setTextColor(99, 102, 241)
        doc.text(flags.join(' '), 165, y)
      }
      y += 4.5
    }

    y += 8
  }

  // Footer on every page
  const totalPages = (doc as jsPDF & { internal: { getNumberOfPages(): number } }).internal.getNumberOfPages()
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i)
    doc.setFontSize(7)
    doc.setTextColor(...TEXT_MID)
    doc.text('Generated by Data Dictionary Agent · TriVector · VIT CodeApex 2025', 10, 290)
    doc.text(`Page ${i} of ${totalPages}`, 200, 290, { align: 'right' })
  }

  doc.save(`data-dictionary-${new Date().toISOString().slice(0, 10)}.pdf`)
}

// ── Export: Query Result ───────────────────────────────────────────────────────

export interface QueryExportData {
  question: string
  sql: string
  explanation: string
  tables_used: string[]
  confidence: number
}

export function exportQueryPDF(queries: QueryExportData[]) {
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' })
  let y = addHeader(doc, 'NL-to-SQL Query Report', `${queries.length} query result${queries.length !== 1 ? 's' : ''}`)

  for (let i = 0; i < queries.length; i++) {
    const q = queries[i]
    y = checkPage(doc, y)

    y = addSectionHeading(doc, `Query ${i + 1}`, y)

    // Question
    doc.setFontSize(9)
    doc.setFont('helvetica', 'bold')
    doc.setTextColor(...TEXT_MID)
    doc.text('Question:', 12, y); y += 5
    doc.setFont('helvetica', 'normal')
    doc.setTextColor(...TEXT_DARK)
    y = addWrappedText(doc, q.question, 12, y, 186)
    y += 4

    // Explanation
    doc.setFont('helvetica', 'bold')
    doc.setTextColor(...TEXT_MID)
    doc.text('Explanation:', 12, y); y += 5
    doc.setFont('helvetica', 'normal')
    doc.setTextColor(...TEXT_DARK)
    y = addWrappedText(doc, q.explanation, 12, y, 186)
    y += 4

    // SQL block
    doc.setFillColor(...BG_CARD)
    const sqlLines = doc.splitTextToSize(q.sql, 182)
    const blockH = sqlLines.length * 4.5 + 8
    doc.roundedRect(10, y, 190, blockH, 2, 2, 'F')
    doc.setFontSize(8)
    doc.setFont('courier', 'normal')
    doc.setTextColor(129, 140, 248)   // indigo-400
    doc.text(sqlLines, 14, y + 6)
    y += blockH + 4

    // Metadata row
    doc.setFontSize(8)
    doc.setFont('helvetica', 'normal')
    doc.setTextColor(...TEXT_MID)
    const scoreColor: [number, number, number] = q.confidence >= 0.8 ? [16, 185, 129] : q.confidence >= 0.5 ? [245, 158, 11] : [239, 68, 68]
    doc.setTextColor(...scoreColor)
    doc.text(`Confidence: ${Math.round(q.confidence * 100)}%`, 12, y)
    doc.setTextColor(...TEXT_MID)
    doc.text(`Tables: ${q.tables_used.join(', ')}`, 60, y)
    y += 10
  }

  const totalPages = (doc as jsPDF & { internal: { getNumberOfPages(): number } }).internal.getNumberOfPages()
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i)
    doc.setFontSize(7)
    doc.setTextColor(...TEXT_MID)
    doc.text('Generated by Data Dictionary Agent · TriVector · VIT CodeApex 2025', 10, 290)
    doc.text(`Page ${i} of ${totalPages}`, 200, 290, { align: 'right' })
  }

  doc.save(`query-report-${new Date().toISOString().slice(0, 10)}.pdf`)
}
