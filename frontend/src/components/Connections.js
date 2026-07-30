import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Link, Plus, Trash2, Database } from 'lucide-react';

function Connections() {
  const [connections, setConnections] = useState([]);
  const [form, setForm] = useState({
    name: '', db_type: 'postgresql', host: '', port: 5432, database: '', username: '', password: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => { loadConnections(); }, []);

  const loadConnections = async () => {
    try {
      const { data } = await api.listConnections();
      setConnections(data);
    } catch (err) {}
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!form.name || !form.host || !form.database || !form.username) {
      setError('请填写所有必填字段');
      return;
    }
    setLoading(true);
    try {
      await api.createConnection(form);
      setForm({ name: '', db_type: 'postgresql', host: '', port: 5432, database: '', username: '', password: '' });
      await loadConnections();
    } catch (err) {
      setError(err.response?.data?.detail || '添加失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('确认删除此数据源连接？')) return;
    try {
      await api.deleteConnection(id);
      await loadConnections();
    } catch (err) {}
  };

  return (
    <div>
      <div className="page-header">
        <h2>数据源管理</h2>
        <p>管理你的数据库连接（PostgreSQL / MySQL）</p>
      </div>

      <div className="card">
        <div className="card-header">
          <Plus size={16} style={{ marginRight: '6px', verticalAlign: 'middle' }} />
          添加数据库连接
        </div>

        <form className="training-form" onSubmit={handleSubmit}>
          <div className="training-form-row">
            <div style={{ flex: 1 }}>
              <label style={{ fontSize: '13px', fontWeight: 500, display: 'block', marginBottom: '6px' }}>
                连接名称
              </label>
              <input className="input" value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="例如：生产环境数据库" />
            </div>
            <div>
              <label style={{ fontSize: '13px', fontWeight: 500, display: 'block', marginBottom: '6px' }}>
                数据库类型
              </label>
              <select className="select" value={form.db_type}
                onChange={(e) => setForm({ ...form, db_type: e.target.value, port: e.target.value === 'mysql' ? 3306 : 5432 })}>
                <option value="postgresql">PostgreSQL</option>
                <option value="mysql">MySQL</option>
              </select>
            </div>
          </div>

          <div className="training-form-row">
            <div style={{ flex: 1 }}>
              <label style={{ fontSize: '13px', fontWeight: 500, display: 'block', marginBottom: '6px' }}>主机</label>
              <input className="input" value={form.host}
                onChange={(e) => setForm({ ...form, host: e.target.value })}
                placeholder="localhost" />
            </div>
            <div style={{ width: '120px' }}>
              <label style={{ fontSize: '13px', fontWeight: 500, display: 'block', marginBottom: '6px' }}>端口</label>
              <input className="input" type="number" value={form.port}
                onChange={(e) => setForm({ ...form, port: parseInt(e.target.value) || 0 })} />
            </div>
          </div>

          <div className="training-form-row">
            <div style={{ flex: 1 }}>
              <label style={{ fontSize: '13px', fontWeight: 500, display: 'block', marginBottom: '6px' }}>数据库名</label>
              <input className="input" value={form.database}
                onChange={(e) => setForm({ ...form, database: e.target.value })} />
            </div>
          </div>

          <div className="training-form-row">
            <div style={{ flex: 1 }}>
              <label style={{ fontSize: '13px', fontWeight: 500, display: 'block', marginBottom: '6px' }}>用户名</label>
              <input className="input" value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })} />
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ fontSize: '13px', fontWeight: 500, display: 'block', marginBottom: '6px' }}>密码</label>
              <input className="input" type="password" value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })} />
            </div>
          </div>

          {error && <div className="error-msg">{error}</div>}

          <button className="btn btn-primary" type="submit" disabled={loading}
            style={{ alignSelf: 'flex-start' }}>
            {loading ? '添加中...' : '添加连接'}
          </button>
        </form>
      </div>

      <div className="card">
        <div className="card-header">
          <Database size={16} style={{ marginRight: '6px', verticalAlign: 'middle' }} />
          已连接数据源 ({connections.length})
        </div>

        {connections.length === 0 ? (
          <p style={{ textAlign: 'center', padding: '24px', color: '#94a3b8' }}>
            暂无数据源，请添加数据库连接
          </p>
        ) : (
          <div>
            {connections.map((c) => (
              <div key={c.id} className="flex items-center justify-between"
                style={{ padding: '12px 0', borderBottom: '1px solid #f1f5f9' }}>
                <div>
                  <div className="flex items-center gap-2" style={{ fontWeight: 500, marginBottom: '4px' }}>
                    <Database size={16} color="#2563eb" />
                    {c.name}
                    <span style={{
                      fontSize: '11px', background: '#dbeafe', color: '#2563eb',
                      padding: '2px 6px', borderRadius: '10px', textTransform: 'uppercase',
                    }}>
                      {c.db_type}
                    </span>
                  </div>
                  <div className="text-sm text-secondary">
                    {c.host}:{c.port}/{c.database}
                  </div>
                </div>
                <button className="btn btn-danger btn-sm" onClick={() => handleDelete(c.id)}>
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default Connections;
