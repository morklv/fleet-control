import type { FleetEvent } from "../types";

export function EventFeed({ events }: { events: FleetEvent[] }) {
  return (
    <section className="event-feed">
      <div className="section-heading">
        <div>
          <span className="section-kicker">SYSTEM ACTIVITY</span>
          <h2>Event log</h2>
        </div>
        <span className="section-count">{events.length}</span>
      </div>
      <div className="events">
        {[...events].reverse().slice(0, 8).map((event, index) => (
          <div className={`event ${event.kind.includes("failed") ? "critical" : ""}`} key={`${event.tick}-${event.kind}-${index}`}>
            <time>T+{event.tick.toString().padStart(4, "0")}</time>
            <span>{event.message}</span>
          </div>
        ))}
        {!events.length && <p className="empty-state">No events yet.</p>}
      </div>
    </section>
  );
}
