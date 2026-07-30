import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Database, UserPlus, LogIn } from 'lucide-react';
import { api } from '../api/client';

function LoginPage() {
  const [mode, setMode] = useState('login'); // login | register
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(username, password);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.detail || '登录失败，请检查凭据');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!username.trim() || !email.trim() || !password) {
      setError('请填写所有必填字段');
      return;
    }
    if (password !== confirmPassword) {
      setError('两次输入的密码不一致');
      return;
    }
    if (password.length < 6) {
      setError('密码至少需要6个字符');
      return;
    }

    setLoading(true);
    try {
      await api.register({ username, email, password });
      setSuccess('注册成功！请登录');
      setMode('login');
      setPassword('');
      setConfirmPassword('');
    } catch (err) {
      setError(err.response?.data?.detail || '注册失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const switchMode = (newMode) => {
    setMode(newMode);
    setError('');
    setSuccess('');
    setPassword('');
    setConfirmPassword('');
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div style={{ textAlign: 'center', marginBottom: '12px' }}>
          <Database size={40} color="#2563eb" />
        </div>
        <h1>Data Analysis Agent</h1>
        <p className="subtitle">AI驱动的智能数据分析平台</p>

        {/* Mode Tabs */}
        <div style={{ display: 'flex', marginBottom: '20px', borderBottom: '1px solid #e2e8f0' }}>
          <button
            onClick={() => switchMode('login')}
            style={{
              flex: 1,
              padding: '10px',
              border: 'none',
              background: 'none',
              fontSize: '14px',
              fontWeight: mode === 'login' ? 600 : 400,
              color: mode === 'login' ? '#2563eb' : '#94a3b8',
              borderBottom: mode === 'login' ? '2px solid #2563eb' : '2px solid transparent',
              cursor: 'pointer',
              transition: 'all 0.15s',
            }}
          >
            <LogIn size={14} style={{ marginRight: '6px', verticalAlign: 'middle' }} />
            登录
          </button>
          <button
            onClick={() => switchMode('register')}
            style={{
              flex: 1,
              padding: '10px',
              border: 'none',
              background: 'none',
              fontSize: '14px',
              fontWeight: mode === 'register' ? 600 : 400,
              color: mode === 'register' ? '#2563eb' : '#94a3b8',
              borderBottom: mode === 'register' ? '2px solid #2563eb' : '2px solid transparent',
              cursor: 'pointer',
              transition: 'all 0.15s',
            }}
          >
            <UserPlus size={14} style={{ marginRight: '6px', verticalAlign: 'middle' }} />
            注册
          </button>
        </div>

        {error && <div className="error-msg">{error}</div>}
        {success && (
          <div style={{ background: '#f0fdf4', color: '#16a34a', padding: '10px 12px', borderRadius: '8px', fontSize: '13px', marginBottom: '16px' }}>
            {success}
          </div>
        )}

        {mode === 'login' ? (
          <form onSubmit={handleLogin}>
            <div className="form-group">
              <label>用户名</label>
              <input
                className="input"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="请输入用户名"
                required
              />
            </div>
            <div className="form-group">
              <label>密码</label>
              <input
                className="input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="请输入密码"
                required
              />
            </div>
            <button className="btn btn-primary login-btn" type="submit" disabled={loading}>
              {loading ? <span className="spinner" /> : <LogIn size={16} />}
              {loading ? '登录中...' : '登录'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleRegister}>
            <div className="form-group">
              <label>用户名 *</label>
              <input
                className="input"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="请输入用户名"
                required
              />
            </div>
            <div className="form-group">
              <label>邮箱 *</label>
              <input
                className="input"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="请输入邮箱"
                required
              />
            </div>
            <div className="form-group">
              <label>密码 *</label>
              <input
                className="input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="至少6个字符"
                required
              />
            </div>
            <div className="form-group">
              <label>确认密码 *</label>
              <input
                className="input"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="再次输入密码"
                required
              />
            </div>
            <button className="btn btn-primary login-btn" type="submit" disabled={loading}>
              {loading ? <span className="spinner" /> : <UserPlus size={16} />}
              {loading ? '注册中...' : '注册'}
            </button>
            <p style={{ textAlign: 'center', marginTop: '12px', fontSize: '13px', color: '#94a3b8' }}>
              注册后默认角色为 analyst
            </p>
          </form>
        )}

        <p style={{ textAlign: 'center', marginTop: '20px', fontSize: '13px', color: '#94a3b8' }}>
          支持 PostgreSQL / MySQL 数据源
        </p>
      </div>
    </div>
  );
}

export default LoginPage;
