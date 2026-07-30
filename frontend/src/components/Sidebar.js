import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  Database, Search, Clock, BookOpen, Link, LogOut, BarChart3,
} from 'lucide-react';

const navItems = [
  { id: 'query', label: 'SQL 查询', icon: Search, path: '/' },
  { id: 'history', label: '历史记录', icon: Clock, path: '/history' },
  { id: 'training', label: '训练管理', icon: BookOpen, path: '/training' },
  { id: 'connections', label: '数据源', icon: Link, path: '/connections' },
];

function Sidebar({ activeTab, onTabChange }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleNav = (item) => {
    onTabChange(item.id);
    navigate(item.path);
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h2>
          <BarChart3 size={20} />
          Data Agent
        </h2>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <button
            key={item.id}
            className={`nav-item ${activeTab === item.id ? 'active' : ''}`}
            onClick={() => handleNav(item)}
          >
            <item.icon size={18} />
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="user-info">
          <div className="user-avatar">
            {user?.username?.charAt(0).toUpperCase()}
          </div>
          <div>
            <div className="user-name">{user?.username}</div>
            <div className="user-role">{user?.role}</div>
          </div>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={handleLogout}
          style={{ width: '100%' }}>
          <LogOut size={14} /> 退出登录
        </button>
      </div>
    </div>
  );
}

export default Sidebar;
