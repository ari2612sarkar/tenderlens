import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import "./index.css";
import { Layout } from "./components/Layout";
import { Analyze } from "./pages/Analyze";
import { Home } from "./pages/Home";
import { Profile } from "./pages/Profile";
import { Report } from "./pages/Report";
import { Schemes } from "./pages/Schemes";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="analyze" element={<Analyze />} />
          <Route path="report/:id" element={<Report />} />
          <Route path="profile" element={<Profile />} />
          <Route path="schemes" element={<Schemes />} />
          <Route path="*" element={<Home />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
);
