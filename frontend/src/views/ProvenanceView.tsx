import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useSessionStore } from "../store/sessionStore";

export function ProvenanceView() {
  const citations = useSessionStore((state) => state.provenance);

  return (
    <Card
      className="phase-panel"
      data-testid="provenance-view"
      aria-label="Provenance"
    >
      <CardHeader className="phase-panel__header">
        <div>
          <CardTitle className="panel-title">Provenance</CardTitle>
          <CardDescription className="panel-subtitle">
            {citations.length} cited chunks
          </CardDescription>
        </div>
      </CardHeader>
      <CardContent className="phase-panel__content">
        <ScrollArea className="provenance-list">
          <div className="provenance-list__inner">
            {citations.length === 0 ? (
              <div className="phase-empty">No citations returned yet.</div>
            ) : null}
            {citations
              .slice(-5)
              .reverse()
              .map((item) => (
                <article key={item.id} className="provenance-row">
                  <div className="provenance-row__top">
                    <strong>{item.citation || item.source}</strong>
                    {item.corpus ? (
                      <Badge variant="outline">{item.corpus}</Badge>
                    ) : null}
                  </div>
                  {item.text ? <p>{item.text}</p> : null}
                </article>
              ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
