import React, { useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import SqlQuery from '../components/SqlQuery';
import History from '../components/History';
import Training from '../components/Training';
import Connections from '../components/Connections';

function MainPage() {
  const [activeTab, setActiveTab] = useState('query');

  return (
    <div className="layout">
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />
      <div className="main-content">
        <Routes>
          <Route path="/" element={<SqlQuery />} />
          <Route path="/history" element={<History />} />
          <Route path="/training" element={<Training />} />
          <Route path="/connections" element={<Connections />} />
        </Routes>
        {window.location.pathname === '/' && !window.location.hash && <SqlQuery />}
      </div>
    </div>
  );
}

export default MainPage;
