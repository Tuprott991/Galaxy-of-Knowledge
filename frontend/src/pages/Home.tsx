import { InsightButton } from "@/components/layout/insight-button";
import { HelpButton } from "@/components/layout/help-button";
import { SearchBar } from "@/components/layout/search-bar";
import { PaperDetail } from "@/components/layout/paper-detail";
import { Chatbot } from "@/components/layout/chatbot";
import { ESCButton } from "@/components/layout/esc-button";
import { useGlobal } from "@/context/GlobalContext";
import TestComponent from "./Test"


export default function Home() {
  const { chatView } = useGlobal();

  return (
    <div className="relative min-h-screen min-w-screen flex items-center justify-center bg-neutral-950 text-neutral-100">
      {!chatView ? (
        <>
          {/* Logo góc trái */}
          <div className="fixed top-4 left-4 select-none z-10">
            <p className="text-xl font-semibold tracking-tight">
              <span className="text-green-400">Soft</span>
              <span className="text-white">AI</span>
            </p>
          </div>

          {/* Nút Insight góc phải */}
          <div className="fixed top-4 right-4 z-10">
            <InsightButton />
          </div>

          {/* Ô tìm kiếm trung tâm */}
          <div className="fixed top-4 left-1/2 -translate-x-1/2 z-10">
            <SearchBar />
          </div>

          {/* Nút Help góc phải dưới */}
          <div className="fixed bottom-4 right-4 z-10">
            <HelpButton />
          </div>
        </>
      ) : (
        <>
          <div className="fixed top-4 left-4 z-10">
            <PaperDetail />
          </div>

          <div className="fixed bottom-4 right-4 z-10">
            <Chatbot />
          </div>

          <div className="fixed bottom-4 left-4 z-10">
            <ESCButton />
          </div>
        </>
      )
      }
      <div className="z-5">
        <TestComponent />
      </div>
    </div >
  );
}
