import { Navigate, Route, Routes } from 'react-router-dom';

import NotebookListPage from './pages/NotebookListPage';
import NotebookWorkspacePage from './pages/NotebookWorkspacePage';

const App = () => {
  return (
    <Routes>
      <Route path="/" element={<NotebookListPage />} />
      <Route path="/notebooks/:notebookId" element={<NotebookWorkspacePage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export default App;
