import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import "./index.css";
import { Toaster } from "@/components/ui/sonner";
import { AppProvider } from "./app/provider";
import { createRouter } from "./app/router";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AppProvider>
      <RouterProvider router={createRouter()} />
      <Toaster />
    </AppProvider>
  </StrictMode>,
);
