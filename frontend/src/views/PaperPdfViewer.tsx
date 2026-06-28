import { ExternalLinkIcon, FileTextIcon } from "lucide-react";
import type { ProvenanceCitation } from "../store/sessionStore";

type Props = {
  citation: ProvenanceCitation | null;
};

/**
 * Resolve an embeddable PDF URL for a citation:
 *  - a direct pdf_url (arXiv, or SSRN when a direct PDF is known) is embedded as-is;
 *  - a local_pdf_path is served through the sandboxed backend route (approved dirs only);
 *  - otherwise there is no PDF to show.
 */
export function pdfHrefFor(citation: ProvenanceCitation | null): string | null {
  if (!citation) return null;
  if (citation.pdfUrl && /^https?:\/\//i.test(citation.pdfUrl)) {
    return citation.pdfUrl;
  }
  if (citation.localPdfPath) {
    return `/api/pdfs?path=${encodeURIComponent(citation.localPdfPath)}`;
  }
  return null;
}

export function PaperPdfViewer({ citation }: Props) {
  const href = pdfHrefFor(citation);
  const sourcePage = citation?.sourceUrl || citation?.source;

  if (!citation) {
    return (
      <div className="pdf-viewer pdf-viewer--empty" data-testid="pdf-viewer">
        <FileTextIcon aria-hidden />
        <p>Select a source with a PDF to preview it here.</p>
      </div>
    );
  }

  if (!href) {
    return (
      <div className="pdf-viewer pdf-viewer--empty" data-testid="pdf-viewer">
        <FileTextIcon aria-hidden />
        <p>PDF not available.</p>
        {sourcePage && /^https?:\/\//i.test(sourcePage) ? (
          <a
            className="pdf-viewer__link"
            href={sourcePage}
            target="_blank"
            rel="noreferrer noopener"
          >
            <ExternalLinkIcon data-icon="inline-start" aria-hidden />
            Open source page instead
          </a>
        ) : null}
      </div>
    );
  }

  return (
    <div className="pdf-viewer" data-testid="pdf-viewer">
      <div className="pdf-viewer__bar">
        <span
          className="pdf-viewer__title"
          title={citation.title || citation.citation}
        >
          {citation.title || citation.citation || "PDF"}
        </span>
        <a
          className="pdf-viewer__link"
          href={href}
          target="_blank"
          rel="noreferrer noopener"
        >
          <ExternalLinkIcon data-icon="inline-start" aria-hidden />
          New tab
        </a>
      </div>
      <object
        className="pdf-viewer__frame"
        data={href}
        type="application/pdf"
        aria-label={`PDF preview: ${citation.title || citation.citation}`}
      >
        {/* Fallback for browsers that refuse to embed the object (e.g. cross-origin X-Frame-Options). */}
        <iframe
          className="pdf-viewer__frame"
          src={href}
          title={`PDF preview: ${citation.title || citation.citation}`}
        />
        <div className="pdf-viewer__fallback">
          <p>Your browser blocked the embedded preview.</p>
          <a href={href} target="_blank" rel="noreferrer noopener">
            Open the PDF in a new tab
          </a>
        </div>
      </object>
    </div>
  );
}
