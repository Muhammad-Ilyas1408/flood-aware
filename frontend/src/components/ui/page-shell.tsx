import * as React from "react";

import { cn } from "@/lib/utils";

function PageShell({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="page-shell"
      className={cn(
        "mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 sm:py-10 lg:px-8",
        className
      )}
      {...props}
    />
  );
}

export { PageShell };
