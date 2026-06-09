"use client";

import { createContext, useContext, useState, type ReactNode } from "react";
import { type PipelineResponse } from "./api";

interface ExplanationData {
  verdict: string;
  perOrder: Record<string, string>;
}

type PipelineStep = "idle" | "running" | "explaining" | "done";

interface DispatchState {
  step: PipelineStep;
  result: PipelineResponse | null;
  explanations: ExplanationData | null;
  selectedOrder: string | null;
  error: string | null;
}

interface DispatchContextValue extends DispatchState {
  setStep: (step: PipelineStep) => void;
  setResult: (result: PipelineResponse | null) => void;
  setExplanations: (data: ExplanationData | null) => void;
  setSelectedOrder: (orderId: string | null) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

const DispatchContext = createContext<DispatchContextValue | null>(null);

export function DispatchProvider({ children }: { children: ReactNode }) {
  const [step, setStep] = useState<PipelineStep>("idle");
  const [result, setResult] = useState<PipelineResponse | null>(null);
  const [explanations, setExplanations] = useState<ExplanationData | null>(null);
  const [selectedOrder, setSelectedOrder] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reset = () => {
    setStep("idle");
    setResult(null);
    setExplanations(null);
    setSelectedOrder(null);
    setError(null);
  };

  return (
    <DispatchContext.Provider
      value={{
        step, result, explanations, selectedOrder, error,
        setStep, setResult, setExplanations, setSelectedOrder, setError, reset,
      }}
    >
      {children}
    </DispatchContext.Provider>
  );
}

export function useDispatch() {
  const ctx = useContext(DispatchContext);
  if (!ctx) throw new Error("useDispatch must be used within DispatchProvider");
  return ctx;
}

export type { ExplanationData, PipelineStep };
