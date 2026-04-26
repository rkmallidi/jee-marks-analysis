import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "@/context/AuthContext";
import ProtectedRoute from "@/components/layout/ProtectedRoute";
import AppShell from "@/components/layout/AppShell";
import LoginPage from "@/pages/LoginPage";
import DashboardOverallPage from "@/pages/DashboardOverallPage";
import DashboardWeakStudentsPage from "@/pages/DashboardWeakStudentsPage";
import DashboardSubjectPage from "@/pages/DashboardSubjectPage";
import DashboardTopicHeatmapPage from "@/pages/DashboardTopicHeatmapPage";
import StudentDeepDivePage from "@/pages/StudentDeepDivePage";
import StudentsPage from "@/pages/StudentsPage";
import ExamsPage from "@/pages/ExamsPage";
import QuestionPaperPage from "@/pages/QuestionPaperPage";
import UploadConsolePage from "@/pages/UploadConsolePage";
import AlertsPage from "@/pages/AlertsPage";
import LeaderboardPage from "@/pages/LeaderboardPage";
import SettingsPage from "@/pages/SettingsPage";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />

          <Route
            element={
              <ProtectedRoute>
                <AppShell />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/dashboard/overall" replace />} />
            <Route path="dashboard/overall"       element={<DashboardOverallPage />} />
            <Route path="dashboard/weak-students" element={<DashboardWeakStudentsPage />} />
            <Route path="dashboard/subjects"      element={<DashboardSubjectPage />} />
            <Route path="dashboard/topics"        element={<DashboardTopicHeatmapPage />} />
            <Route path="dashboard/leaderboard"   element={<LeaderboardPage />} />
            <Route path="students"                element={<StudentsPage />} />
            <Route path="students/:admission_no"  element={<StudentDeepDivePage />} />
            <Route path="exams"                   element={<ExamsPage />} />
            <Route path="questions"               element={<QuestionPaperPage />} />
            <Route path="uploads"                 element={<UploadConsolePage />} />
            <Route path="alerts"                  element={<AlertsPage />} />
            <Route path="settings"                element={<SettingsPage />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
