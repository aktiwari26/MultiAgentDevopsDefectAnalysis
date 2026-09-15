import { useRef, useEffect } from 'react';
import { Routes, Route, useLocation, Navigate } from 'react-router-dom';
import gsap from 'gsap';
import Sidebar from './components/Sidebar';
import Home from './pages/Home';
import Analytics from './pages/Analytics';
import RagTuning from './pages/RagTuning';
import LandingPage from './pages/LandingPage';
import Docs from './pages/Docs';

function PageTransition({ children }) {
  const pageRef = useRef(null);
  const location = useLocation();

  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.fromTo(
        pageRef.current,
        { opacity: 0, y: 20 },
        { opacity: 1, y: 0, duration: 0.4, ease: 'power2.out' }
      );
    }, pageRef);
    return () => ctx.revert();
  }, [location.pathname]);

  return (
    <div ref={pageRef} className="min-h-0">
      {children}
    </div>
  );
}

function DashboardLayout() {
  const mainRef = useRef(null);
  const location = useLocation();

  useEffect(() => {
    gsap.fromTo(mainRef.current, { opacity: 0 }, { opacity: 1, duration: 0.5 });
  }, []);

  return (
    <div className="flex min-h-screen bg-surface">
      <Sidebar />
      <main
        ref={mainRef}
        className="flex-1 ml-64 p-8 overflow-y-auto"
        style={{ minHeight: '100vh' }}
      >
        <Routes>
          <Route
            path="/"
            element={
              <PageTransition>
                <Home />
              </PageTransition>
            }
          />
          <Route
            path="/analytics"
            element={
              <PageTransition>
                <Analytics />
              </PageTransition>
            }
          />
          <Route
            path="/rag"
            element={
              <PageTransition>
                <RagTuning />
              </PageTransition>
            }
          />
          <Route
            path="/docs"
            element={
              <PageTransition>
                <Docs />
              </PageTransition>
            }
          />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/dashboard/*" element={<DashboardLayout />} />
      {/* Redirect any old links to dashboard */}
      <Route path="/analytics" element={<Navigate to="/dashboard/analytics" replace />} />
      <Route path="/rag" element={<Navigate to="/dashboard/rag" replace />} />
      <Route path="/docs" element={<Navigate to="/dashboard/docs" replace />} />
    </Routes>
  );
}
