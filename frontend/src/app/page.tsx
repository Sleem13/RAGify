"use client";

import Link from 'next/link';
import { ArrowRight, BarChart3, BookOpen, CheckCircle2, MessageSquareText, ScrollText, Search, ShieldCheck, Sparkles } from 'lucide-react';
import { BrandMark } from '@/components/BrandMark';
import { ThemeControls } from '@/components/ThemeControls';
import { useAppContext } from '@/context/AppContext';

export default function Home() {
  const { t } = useAppContext();
  const features = [
    { icon: ScrollText, title: t('feature1Title'), desc: t('feature1Desc') },
    { icon: BarChart3, title: t('feature2Title'), desc: t('feature2Desc') },
    { icon: Search, title: 'Cited discovery', desc: 'Trace every answer back to its document and PDF page.' },
    { icon: MessageSquareText, title: t('feature4Title'), desc: t('feature4Desc') },
    { icon: ShieldCheck, title: t('feature5Title'), desc: t('feature5Desc') },
    { icon: Sparkles, title: t('feature6Title'), desc: t('feature6Desc') },
  ];

  return (
    <main className="egypt-shell min-h-screen overflow-hidden text-[#20180f] dark:text-[#f8eccf]">
      <nav className="hieroglyph-band sticky top-0 z-50 border-b border-[#b98332]/25 bg-[#fff9e8]/90 backdrop-blur-xl dark:bg-[#061521]/90">
        <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-6">
          <BrandMark />
          <div className="hidden items-center gap-8 text-sm font-semibold text-[#765326] md:flex">
            <a href="#journey" className="hover:text-[#123c69] dark:text-[#d6bd83] dark:hover:text-[#f3d77b]">The journey</a>
            <a href="#features" className="hover:text-[#123c69] dark:text-[#d6bd83] dark:hover:text-[#f3d77b]">The collection</a>
          </div>
          <div className="flex items-center gap-3">
            <ThemeControls />
            <Link href="/dashboard" className="gold-button hidden rounded-full px-5 py-2.5 text-sm font-bold transition sm:inline-flex">
              Enter the archive
            </Link>
          </div>
        </div>
      </nav>

      <section className="relative mx-auto grid min-h-[720px] max-w-7xl items-center gap-12 px-6 py-20 lg:grid-cols-[1.1fr_.9fr]">
        <div className="relative z-10">
          <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-[#d6a63a]/45 bg-[#fff9e8]/70 px-4 py-2 text-xs font-bold uppercase tracking-[0.18em] text-[#8a6024] dark:bg-[#0b2840]/70 dark:text-[#f3d77b]">
            <BookOpen className="h-4 w-4" /> Ancient knowledge · modern intelligence
          </div>
          <h1 className="display-font max-w-4xl text-5xl font-bold leading-[1.02] text-[#123c69] dark:text-[#f8eccf] md:text-7xl">
            Unearth the wisdom
            <span className="mt-2 block text-[#b37b25] dark:text-[#f3d77b]">inside your documents.</span>
          </h1>
          <p className="mt-7 max-w-2xl text-lg leading-8 text-[#684e2e] dark:text-[#d8c8a7]">
            A digital House of Knowledge for PDFs, manuscripts, reports, and data. Upload a collection, ask precise questions, and receive grounded answers with page-level citations.
          </p>
          <div className="mt-10 flex flex-wrap gap-4">
            <Link href="/dashboard" className="gold-button inline-flex items-center gap-2 rounded-full px-7 py-4 font-bold transition">
              Begin your research <ArrowRight className="h-5 w-5" />
            </Link>
            <a href="#journey" className="inline-flex items-center rounded-full border border-[#123c69]/25 bg-[#fff9e8]/60 px-7 py-4 font-bold text-[#123c69] transition hover:border-[#d6a63a] dark:bg-[#0b2840]/60 dark:text-[#f8eccf]">
              Explore the process
            </a>
          </div>
          <div className="mt-12 flex flex-wrap gap-x-8 gap-y-3 text-sm text-[#75572f] dark:text-[#cfbc94]">
            {['Local FAISS index', 'Page-level sources', 'English & Arabic'].map(item => (
              <span key={item} className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-[#168c8c]" />{item}</span>
            ))}
          </div>
        </div>

        <div className="relative mx-auto h-[480px] w-full max-w-[500px]">
          <div className="sun-disc absolute left-1/2 top-4 h-52 w-52 -translate-x-1/2" />
          <div className="absolute bottom-0 left-1/2 h-0 w-0 -translate-x-1/2 border-b-[310px] border-l-[220px] border-r-[220px] border-b-[#c9964b] border-l-transparent border-r-transparent drop-shadow-[0_28px_30px_rgba(66,39,10,.25)]" />
          <div className="absolute bottom-0 left-1/2 h-0 w-0 -translate-x-1/2 translate-y-2 border-b-[250px] border-l-[177px] border-r-[177px] border-b-[#dfb568] border-l-transparent border-r-transparent opacity-75" />
          <div className="papyrus-panel absolute bottom-12 left-1/2 w-[78%] -translate-x-1/2 rounded-2xl p-6 backdrop-blur">
            <div className="mb-4 flex items-center justify-between text-xs uppercase tracking-[0.2em] text-[#8a6024] dark:text-[#d6bd83]"><span>Archive query</span><Sparkles className="h-4 w-4 text-[#168c8c]" /></div>
            <p className="display-font text-lg font-bold text-[#123c69] dark:text-[#f3d77b]">“What distinguishes an LLM from a GAN?”</p>
            <div className="mt-5 space-y-2">
              <div className="h-2 w-full rounded bg-[#d6a63a]/25" /><div className="h-2 w-[88%] rounded bg-[#d6a63a]/20" /><div className="h-2 w-[64%] rounded bg-[#168c8c]/25" />
            </div>
            <div className="mt-5 rounded-lg border border-[#168c8c]/25 bg-[#168c8c]/10 px-3 py-2 text-xs font-semibold text-[#126d6d] dark:text-[#77d1cf]">Source: lecture.pdf · page 17</div>
          </div>
        </div>
      </section>

      <section id="journey" className="border-y border-[#b98332]/20 bg-[#123c69] px-6 py-20 text-[#fff9e8]">
        <div className="mx-auto max-w-7xl">
          <p className="text-center text-xs font-bold uppercase tracking-[0.3em] text-[#f3d77b]">From scroll to insight</p>
          <h2 className="display-font mt-3 text-center text-4xl font-bold">A three-stage research journey</h2>
          <div className="mt-12 grid gap-6 md:grid-cols-3">
            {[
              ['01', 'Place it in the archive', 'Upload documents and datasets through a resilient background ingestion queue.'],
              ['02', 'Map the knowledge', 'Text is normalized, embedded, and indexed with page-aware metadata.'],
              ['03', 'Question the collection', 'Hybrid retrieval finds evidence and the assistant answers with citations.'],
            ].map(([step, title, desc]) => (
              <article key={step} className="rounded-2xl border border-[#f3d77b]/20 bg-white/5 p-7">
                <span className="display-font text-4xl font-bold text-[#d6a63a]">{step}</span>
                <h3 className="display-font mt-5 text-xl font-bold">{title}</h3>
                <p className="mt-3 leading-7 text-[#d7c9aa]">{desc}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="features" className="mx-auto max-w-7xl px-6 py-24">
        <div className="max-w-2xl"><p className="text-xs font-bold uppercase tracking-[0.3em] text-[#a46d1f] dark:text-[#f3d77b]">The collection</p><h2 className="display-font mt-3 text-4xl font-bold text-[#123c69] dark:text-[#f8eccf]">Tools worthy of a modern scribe</h2></div>
        <div className="mt-12 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {features.map(({ icon: Icon, title, desc }) => (
            <article key={title} className="egypt-card rounded-2xl border border-[#b98332]/20 p-7 shadow-sm transition hover:-translate-y-1 hover:shadow-xl">
              <div className="grid h-12 w-12 place-items-center rounded-full bg-[#123c69] text-[#f3d77b]"><Icon className="h-6 w-6" /></div>
              <h3 className="display-font mt-5 text-xl font-bold text-[#123c69] dark:text-[#f3d77b]">{title}</h3>
              <p className="mt-3 text-sm leading-7 text-[#6c5233] dark:text-[#cfbf9f]">{desc}</p>
            </article>
          ))}
        </div>
      </section>

      <footer className="hieroglyph-band border-t border-[#b98332]/20 bg-[#fff9e8]/70 px-6 py-10 dark:bg-[#071a2f]">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-5 sm:flex-row"><BrandMark /><p className="text-sm text-[#795c37] dark:text-[#c7b58f]">Built in Egypt’s spirit of preserving and sharing knowledge.</p></div>
      </footer>
    </main>
  );
}
