import { useSessionStore } from "../store/sessionStore";

export function ProvenanceView() {
  const citations = useSessionStore((state) => state.provenance);

  return (
    <section className="phase-panel" data-testid="provenance-view" aria-label="Provenance">
      <header className="phase-panel__header">
        <div>
          <div className="panel-title">Provenance</div>
          <div className="panel-subtitle">{citations.length} cited chunks</div>
        </div>
      </header>
      <div className="provenance-list">
        {citations.length === 0 ? <div className="phase-empty">No citations returned yet.</div> : null}
        {citations.slice(-5).reverse().map((item) => (
          <article key={item.id} className="provenance-row">
            <div className="provenance-row__top">
              <strong>{item.citation || item.source}</strong>
              {item.corpus ? <span>{item.corpus}</span> : null}
            </div>
            {item.text ? <p>{item.text}</p> : null}
          </article>
        ))}
      </div>
    </section>
  );
}
