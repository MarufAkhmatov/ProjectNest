import { useState } from "react";
import { Search, SlidersHorizontal, MoreVertical } from "lucide-react";
import { motion } from "motion/react";

const providers = [
  {
    name: "Dr. Chloe Davis",
    dept: "Pathology",
    contact: "(505) 555-0123",
    available: true,
    img: "https://images.unsplash.com/photo-1594824476967-48c8b964273f?w=56&h=56&fit=crop&auto=format",
  },
  {
    name: "Dr. Ben Carter",
    dept: "Orthopedics",
    contact: "(405) 654-7654",
    available: false,
    img: "https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?w=56&h=56&fit=crop&auto=format",
  },
  {
    name: "Dr. Alice Smith",
    dept: "Pathology",
    contact: "(504) 654-0543",
    available: true,
    img: "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?w=56&h=56&fit=crop&auto=format",
  },
];

export function HealthcareProviders() {
  const [search, setSearch] = useState("");

  const filtered = providers.filter(p =>
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    p.dept.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="bg-card rounded-2xl p-5 flex flex-col gap-4" style={{ backdropFilter: "blur(12px)", border: "1px solid rgba(255,255,255,0.6)" }}>
      <div className="flex items-center justify-between">
        <span style={{ fontSize: "0.9rem", fontWeight: 600, color: "#1a2030" }}>Healthcare Providers</span>
        <div className="flex gap-2">
          <button style={{ width: 32, height: 32, borderRadius: 8, background: "#f0f4f7", border: "none", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Search size={14} color="#6b7a8d" />
          </button>
          <button style={{ display: "flex", alignItems: "center", gap: 4, height: 32, borderRadius: 8, background: "#f0f4f7", border: "none", cursor: "pointer", padding: "0 10px", fontSize: "0.75rem", color: "#6b7a8d" }}>
            <SlidersHorizontal size={12} /> Filter
          </button>
        </div>
      </div>

      {/* Header row */}
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1.2fr 1.3fr 40px", fontSize: "0.72rem", color: "#9aa5b4", paddingBottom: 4, borderBottom: "1px solid #e4eaef" }}>
        <span>Provider Name</span>
        <span>Department</span>
        <span>Contact</span>
        <span>Action</span>
      </div>

      {filtered.map((p, i) => (
        <motion.div
          key={p.name}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.08 }}
          style={{
            display: "grid",
            gridTemplateColumns: "2fr 1.2fr 1.3fr 40px",
            alignItems: "center",
            paddingBottom: i < filtered.length - 1 ? 12 : 0,
            borderBottom: i < filtered.length - 1 ? "1px solid #f0f4f7" : "none",
          }}
        >
          <div className="flex items-center gap-2">
            <img
              src={p.img}
              alt={p.name}
              style={{ width: 32, height: 32, borderRadius: "50%", objectFit: "cover", flexShrink: 0 }}
            />
            <div>
              <div style={{ fontSize: "0.78rem", fontWeight: 500, color: "#1a2030" }}>{p.name}</div>
              <div className="flex items-center gap-1">
                <div style={{ width: 6, height: 6, borderRadius: "50%", background: p.available ? "#2d7a5f" : "#e53e3e" }} />
                <span style={{ fontSize: "0.65rem", color: "#9aa5b4" }}>{p.available ? "Available" : "Absent"}</span>
              </div>
            </div>
          </div>
          <span style={{ fontSize: "0.75rem", color: "#6b7a8d" }}>{p.dept}</span>
          <span style={{ fontSize: "0.75rem", color: "#6b7a8d" }}>{p.contact}</span>
          <button style={{ background: "none", border: "none", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <MoreVertical size={14} color="#9aa5b4" />
          </button>
        </motion.div>
      ))}
    </div>
  );
}
