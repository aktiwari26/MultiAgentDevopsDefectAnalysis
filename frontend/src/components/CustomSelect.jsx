import { useState, useRef, useEffect } from 'react';
import { ChevronRight } from 'lucide-react';

export default function CustomSelect({ label, value, options, onChange, icon: Icon, placeholder = "Select model..." }) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const dropdownRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const filteredOptions = options.filter(opt => 
    (opt.id || "").toLowerCase().includes(search.toLowerCase()) || 
    (opt.name || "").toLowerCase().includes(search.toLowerCase())
  );

  const selectedOption = options.find(opt => opt.id === value) || { name: value, id: value };

  return (
    <div className="space-y-1.5 relative w-full" ref={dropdownRef}>
      {label && <label className="text-[11px] text-slate-500 font-medium block">{label}</label>}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between bg-white/[0.05] border border-white/[0.06] rounded-lg px-3 py-2 text-xs text-slate-300 hover:border-white/20 transition-all focus:outline-none"
      >
        <div className="flex items-center gap-2 overflow-hidden">
          {Icon && <Icon size={14} className="text-slate-500 flex-shrink-0" />}
          <span className="truncate">{selectedOption.name || value}</span>
        </div>
        <ChevronRight size={14} className={`text-slate-600 transition-transform flex-shrink-0 ${isOpen ? 'rotate-90' : 'rotate-0'}`} />
      </button>

      {isOpen && (
        <div className="absolute top-full mt-1 left-0 right-0 bg-slate-900 border border-white/10 rounded-xl shadow-2xl z-[200] overflow-hidden animate-in origin-top">
          <div className="p-2 border-b border-white/5">
            <input
              autoFocus
              type="text"
              placeholder={placeholder}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500/50"
            />
          </div>
          <div className="max-h-60 overflow-y-auto scrollbar-thin scrollbar-thumb-white/10">
            {filteredOptions.length > 0 ? (
              filteredOptions.map((opt) => (
                <button
                  key={opt.id}
                  onClick={() => {
                    onChange(opt.id);
                    setIsOpen(false);
                    setSearch("");
                  }}
                  className={`w-full text-left px-4 py-2 text-xs transition-colors hover:bg-white/5 ${
                    value === opt.id ? 'text-indigo-400 bg-indigo-500/5' : 'text-slate-400'
                  }`}
                >
                  <div className="font-medium">{opt.name}</div>
                  <div className="text-[9px] text-slate-600 truncate">{opt.id}</div>
                </button>
              ))
            ) : (
              <div className="px-4 py-3 text-xs text-slate-600 italic">No items found</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
