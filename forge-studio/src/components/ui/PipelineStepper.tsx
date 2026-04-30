import { cn } from "@/lib/utils";

interface Step { id: number; name: string; }

export function PipelineStepper({ steps, currentStep }: { steps: Step[]; currentStep: number }) {
  return (
    <div className="flex w-full gap-0">
      {steps.map((step, i) => {
        const active = currentStep === step.id;
        const past = currentStep > step.id;
        return (
          <div key={step.id} className="flex-1 flex flex-col items-center gap-1.5">
            <div className="flex items-center w-full">
              <div className={cn(
                "w-5 h-5 rounded-full border flex items-center justify-center font-mono text-[9px] transition-all",
                active ? "border-cyber-cyan bg-cyber-cyan/10 text-cyber-cyan" :
                past   ? "border-cyber-success bg-cyber-success/10 text-cyber-success" :
                         "border-cyber-border text-monolith-muted",
              )}>
                {past ? "✓" : step.id}
              </div>
              {i < steps.length - 1 && (
                <div className={cn("flex-1 h-px", past ? "bg-cyber-success" : "bg-cyber-border")} />
              )}
            </div>
            <span className={cn(
              "font-mono text-[8px] uppercase tracking-widest",
              active ? "text-cyber-cyan" : "text-monolith-muted",
            )}>
              {step.name}
            </span>
          </div>
        );
      })}
    </div>
  );
}
