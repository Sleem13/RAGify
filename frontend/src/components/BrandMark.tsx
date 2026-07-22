import { Pyramid } from 'lucide-react';

export function BrandMark({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <div className="relative grid h-10 w-10 place-items-center rounded-full border border-[#d6a63a]/60 bg-[#123c69] text-[#f3d77b] shadow-lg shadow-[#123c69]/20">
        <Pyramid className="h-5 w-5" />
        <span className="absolute -bottom-1 h-1 w-6 rounded-full bg-[#168c8c]" />
      </div>
      <div className="leading-tight">
        <div className="display-font text-lg font-bold tracking-[0.14em] text-[#123c69] dark:text-[#f3d77b]">RAGIFY</div>
        {!compact && <div className="text-[10px] uppercase tracking-[0.24em] text-[#8c642b] dark:text-[#c9ad6a]">House of Knowledge</div>}
      </div>
    </div>
  );
}
