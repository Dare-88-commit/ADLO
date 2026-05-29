"use client";

type MacroSliderProps = {
  label: string;
  min: number;
  max: number;
  step: number;
  value: number;
  suffix?: string;
  hint?: string;
  onChange: (value: number) => void;
};

export function MacroSlider({
  label,
  min,
  max,
  step,
  value,
  suffix = "",
  hint,
  onChange,
}: MacroSliderProps) {
  return (
    <label className="block rounded-2xl border border-white/10 bg-white/5 p-4">
      <div className="mb-2 flex items-center justify-between gap-4">
        <span className="font-mono text-xs uppercase tracking-[0.32em] text-slate-300">
          {label}
        </span>
        <span className="font-mono text-sm text-sky-300">
          {value.toFixed(2)}
          {suffix}
        </span>
      </div>
      <input
        className="h-2 w-full cursor-pointer appearance-none rounded-full bg-slate-700 accent-sky-400"
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
      {hint ? <p className="mt-3 text-xs text-slate-400">{hint}</p> : null}
    </label>
  );
}
