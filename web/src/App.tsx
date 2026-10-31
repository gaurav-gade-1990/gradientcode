import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router";
import ProblemList from "./pages/ProblemList";
import StudyPlans from "./pages/StudyPlans";
import StudyPlanPage from "./pages/StudyPlanPage";
import Profile from "./pages/Profile";

const ProblemPage = lazy(() => import("./pages/ProblemPage"));

export default function App() {
  return (
    <Suspense fallback={<div className="h-full bg-page" />}>
      <Routes>
        <Route path="/" element={<ProblemList />} />
        <Route path="/problemset" element={<ProblemList />} />
        <Route path="/problems/:slug" element={<ProblemPage />} />
        <Route path="/study-plans" element={<StudyPlans />} />
        <Route path="/study-plans/:id" element={<StudyPlanPage />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
