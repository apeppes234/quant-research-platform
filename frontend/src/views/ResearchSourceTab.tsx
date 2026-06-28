import { useMemo, useState } from "react";
import { ExternalLinkIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  useSessionStore,
  type ProvenanceCitation,
  type ProvenanceProvider,
} from "../store/sessionStore";
import { PaperPdfViewer, pdfHrefFor } from "./PaperPdfViewer";

const PROVIDER_ORDER: ProvenanceProvider[] = [
  "arxiv",
  "ssrn",
  "quantresearch_repo",
  "quantconnect_strategy_library",
  "other",
];

const PROVIDER_LABEL: Record<ProvenanceProvider, string> = {
  arxiv: "arXiv",
  ssrn: "SSRN",
  quantresearch_repo: "QuantResearch",
  quantconnect_strategy_library: "QuantConnect Strategy Library",
  other: "Other sources",
};

export function ResearchSourceTab() {
  const citations = useSessionStore((state) => state.provenance);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const grouped = useMemo(() => groupByProvider(citations), [citations]);
  const pdfSources = useMemo(
    () => citations.filter((item) => pdfHrefFor(item) !== null),
    [citations],
  );

  const selected =
    citations.find((item) => item.id === selectedId) ?? pdfSources[0] ?? null;

  if (citations.length === 0) {
    return (
      <div
        className="research-tab research-tab--empty"
        data-testid="research-tab"
      >
        <p className="phase-empty">
          No research sources yet. When an agent calls{" "}
          <code>search_knowledge</code>, the papers, notebooks, and strategy
          examples it relied on appear here.
        </p>
      </div>
    );
  }

  return (
    <div className="research-tab" data-testid="research-tab">
      {pdfSources.length > 0 ? (
        <div className="research-viewer">
          {pdfSources.length > 1 ? (
            <label className="research-viewer__picker">
              <span className="sr-only">Choose a PDF to preview</span>
              <select
                value={selected?.id ?? ""}
                onChange={(event) => setSelectedId(event.target.value)}
              >
                {pdfSources.map((item) => (
                  <option key={item.id} value={item.id}>
                    {PROVIDER_LABEL[item.provider]} —{" "}
                    {item.title || item.citation || item.source}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          <PaperPdfViewer citation={selected} />
        </div>
      ) : null}

      <ScrollArea className="research-list">
        <div className="research-list__inner">
          {PROVIDER_ORDER.filter((provider) => grouped[provider]?.length).map(
            (provider) => (
              <section key={provider} className="research-group">
                <header className="research-group__header">
                  <span>{PROVIDER_LABEL[provider]}</span>
                  <Badge variant="secondary">{grouped[provider].length}</Badge>
                </header>
                {grouped[provider].map((item) => (
                  <SourceCard
                    key={item.id}
                    item={item}
                    active={item.id === selected?.id}
                    onSelect={() => setSelectedId(item.id)}
                  />
                ))}
              </section>
            ),
          )}
        </div>
      </ScrollArea>
    </div>
  );
}

function SourceCard({
  item,
  active,
  onSelect,
}: {
  item: ProvenanceCitation;
  active: boolean;
  onSelect: () => void;
}) {
  const hasPdf = pdfHrefFor(item) !== null;
  const link = item.sourceUrl || (isUrl(item.source) ? item.source : undefined);
  const meta = item.metadata ?? {};
  const facets = [
    metaString(meta.strategy_family),
    metaString(meta.asset_class),
    metaString(meta.signal_type),
  ].filter(Boolean) as string[];

  return (
    <article
      className={`research-card${active ? " research-card--active" : ""}`}
      onClick={onSelect}
      role="button"
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSelect();
        }
      }}
      data-testid="research-card"
    >
      <div className="research-card__top">
        <strong>{item.title || item.citation || item.source}</strong>
        {hasPdf ? <Badge variant="default">PDF</Badge> : null}
      </div>

      <div className="research-card__badges">
        {item.corpus ? <Badge variant="outline">{item.corpus}</Badge> : null}
        {facets.map((facet) => (
          <Badge key={facet} variant="secondary">
            {facet}
          </Badge>
        ))}
        {item.cellType ? (
          <Badge variant="outline">
            {item.cellType}
            {item.cellIndex !== undefined ? ` · cell ${item.cellIndex}` : ""}
          </Badge>
        ) : null}
        {item.pageNumber !== undefined ? (
          <Badge variant="outline">p. {item.pageNumber}</Badge>
        ) : null}
      </div>

      {item.sourcePath ? (
        <code className="research-card__path">{item.sourcePath}</code>
      ) : null}

      {item.text ? <p className="research-card__snippet">{item.text}</p> : null}

      {item.tags.length > 0 ? (
        <div className="research-card__tags">
          {item.tags.slice(0, 8).map((tag) => (
            <span key={tag} className="research-tag">
              {tag}
            </span>
          ))}
        </div>
      ) : null}

      <div className="research-card__footer">
        {item.agentName ? (
          <span className="research-card__agent">via {item.agentName}</span>
        ) : (
          <span />
        )}
        {link ? (
          <a
            href={link}
            target="_blank"
            rel="noreferrer noopener"
            onClick={(event) => event.stopPropagation()}
          >
            <ExternalLinkIcon data-icon="inline-start" aria-hidden />
            Source
          </a>
        ) : null}
      </div>
    </article>
  );
}

function groupByProvider(
  citations: ProvenanceCitation[],
): Record<ProvenanceProvider, ProvenanceCitation[]> {
  const groups: Record<ProvenanceProvider, ProvenanceCitation[]> = {
    arxiv: [],
    ssrn: [],
    quantresearch_repo: [],
    quantconnect_strategy_library: [],
    other: [],
  };
  for (const citation of citations) {
    groups[citation.provider].push(citation);
  }
  return groups;
}

function metaString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function isUrl(value: string): boolean {
  return /^https?:\/\//i.test(value);
}
