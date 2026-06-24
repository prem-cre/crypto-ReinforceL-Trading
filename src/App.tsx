import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ConfigProvider, theme } from 'antd';
import { Dashboard } from './pages/Dashboard';
import { Home } from './pages/Home';

const App: React.FC = () => {
  return (
    <ConfigProvider
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorPrimary: '#7c3aed',
          colorBgContainer: '#161b27',
          colorBgElevated: '#1e2535',
          colorBorder: 'rgba(255,255,255,0.08)',
          borderRadius: 10,
          fontFamily: "'Inter', system-ui, sans-serif",
        },
        components: {
          Layout:  { bodyBg: '#0d1117', headerBg: '#111827', siderBg: '#111827' },
          Card:    { colorBgContainer: '#161b27' },
          Table:   { colorBgContainer: 'transparent', headerBg: 'rgba(255,255,255,0.03)' },
          Select:  { colorBgContainer: 'rgba(255,255,255,0.04)' },
          Input:   { colorBgContainer: 'rgba(255,255,255,0.04)' },
          DatePicker: { colorBgContainer: 'rgba(255,255,255,0.04)' },
        },
      }}
    >
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/dashboard" element={<Dashboard />} />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
};

export default App;
