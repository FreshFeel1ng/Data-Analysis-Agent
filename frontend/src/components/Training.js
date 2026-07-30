import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { BookOpen, Plus, Trash2, Upload, FileText } from 'lucide-react';

const TRAINING_TYPES = [
  { value: 'ddl', label: 'DDL 语句', desc: '直接提供完整的 CREATE TABLE 建表语句' },
  { value: 'schema', label: '数据库 Schema', desc: '执行查询语句获取表结构信息' },
  { value: 'documentation', label: '文档 (Documentation)', desc: '提供业务术语、指标定义等补充说明' },
  { value: 'sql_example', label: '已有 SQL 查询', desc: '提供正确的、带自然语言描述的 SQL 示例' },
];

function Training() {
  const [trainings, setTrainings] = useState([]);
  const [connections, setConnections] = useState([]);
  const [form, setForm] = useState({
    training_type: 'ddl',
    db_connection_id: '',
    content: '',
    description: '',
    question: '',
    sql: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadTrainings();
    api.listConnections().then(({ data }) => setConnections(data)).catch(() => {});
  }, []);

  const loadTrainings = async () => {
    try {
      const { data } = await api.listTrainings();
      setTrainings(data);
    } catch (err) {}
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!form.content.trim()) {
      setError('内容不能为空');
      return;
    }
    if (form.training_type === 'sql_example' && (!form.question || !form.sql)) {
      setError('SQL 示例需要同时提供问题和 SQL');
      return;
    }

    setLoading(true);
    try {
      const payload = {
        training_type: form.training_type,
        content: form.content,
        description: form.description || null,
        question: form.training_type === 'sql_example' ? form.question : null,
        sql: form.training_type === 'sql_example' ? form.sql : null,
        db_connection_id: form.db_connection_id ? parseInt(form.db_connection_id) : null,
      };
      await api.addTraining(payload);
      setForm({ training_type: 'ddl', db_connection_id: '', content: '', description: '', question: '', sql: '' });
      await loadTrainings();
    } catch (err) {
      setError(err.response?.data?.detail || '添加失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('确认删除？')) return;
    try {
      await api.deleteTraining(id);
      await loadTrainings();
    } catch (err) {}
  };

  const handleAutoImport = async () => {
    if (!form.db_connection_id) {
      setError('请先选择数据源');
      return;
    }
    setLoading(true);
    try {
      const { data } = await api.autoImportSchema(parseInt(form.db_connection_id));
      alert(data.message);
      await loadTrainings();
    } catch (err) {
      setError(err.response?.data?.detail || '导入失败');
    } finally {
      setLoading(false);
    }
  };

  const getBadgeClass = (type) => {
    const map = { ddl: 'badge-ddl', schema: 'badge-schema', documentation: 'badge-documentation', sql_example: 'badge-sql_example' };
    return map[type] || '';
  };

  const typeLabels = { ddl: 'DDL', schema: 'Schema', documentation: '文档', sql_example: 'SQL示例' };

  return (
    <div>
      <div className="page-header">
        <h2>训练管理</h2>
        <p>添加训练数据以帮助 AI 更好地理解你的数据库结构和业务逻辑</p>
      </div>

      <div className="card">
        <div className="card-header">
          <Plus size={16} style={{ marginRight: '6px', verticalAlign: 'middle' }} />
          添加训练数据
        </div>

        <form className="training-form" onSubmit={handleSubmit}>
          <div>
            <label style={{ fontSize: '13px', fontWeight: 500, display: 'block', marginBottom: '6px' }}>
              训练类型
            </label>
            <select
              className="select"
              value={form.training_type}
              onChange={(e) => setForm({ ...form, training_type: e.target.value })}
            >
              {TRAINING_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
            <p className="text-sm text-secondary mt-2">
              {TRAINING_TYPES.find((t) => t.value === form.training_type)?.desc}
            </p>
          </div>

          <div className="training-form-row">
            <div style={{ flex: 1 }}>
              <label style={{ fontSize: '13px', fontWeight: 500, display: 'block', marginBottom: '6px' }}>
                关联数据源
              </label>
              <select
                className="select"
                value={form.db_connection_id}
                onChange={(e) => setForm({ ...form, db_connection_id: e.target.value })}
              >
                <option value="">全局（所有数据源）</option>
                {connections.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label style={{ fontSize: '13px', fontWeight: 500, display: 'block', marginBottom: '6px' }}>
              {form.training_type === 'sql_example' ? '说明（可选）' : '内容'}
            </label>
            <textarea
              className="textarea"
              value={form.content}
              onChange={(e) => setForm({ ...form, content: e.target.value })}
              placeholder={
                form.training_type === 'ddl'
                  ? 'CREATE TABLE users (\n  id SERIAL PRIMARY KEY,\n  name VARCHAR(100),\n  created_at TIMESTAMP\n);'
                  : form.training_type === 'documentation'
                  ? 'GMV = 成交总额，包含已付款和未付款订单...'
                  : '输入训练内容...'
              }
              rows={form.training_type === 'ddl' || form.training_type === 'sql_example' ? 6 : 4}
            />
          </div>

          {form.training_type === 'sql_example' && (
            <>
              <div>
                <label style={{ fontSize: '13px', fontWeight: 500, display: 'block', marginBottom: '6px' }}>
                  自然语言问题
                </label>
                <input
                  className="input"
                  value={form.question}
                  onChange={(e) => setForm({ ...form, question: e.target.value })}
                  placeholder="例如：查询上个月销售额前十的产品"
                />
              </div>
              <div>
                <label style={{ fontSize: '13px', fontWeight: 500, display: 'block', marginBottom: '6px' }}>
                  SQL 语句
                </label>
                <textarea
                  className="textarea"
                  value={form.sql}
                  onChange={(e) => setForm({ ...form, sql: e.target.value })}
                  placeholder="SELECT product_name, SUM(amount) ..."
                  rows={4}
                />
              </div>
            </>
          )}

          <div>
            <label style={{ fontSize: '13px', fontWeight: 500, display: 'block', marginBottom: '6px' }}>
              描述（可选）
            </label>
            <input
              className="input"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="简要描述此训练数据的用途"
            />
          </div>

          {error && <div className="error-msg">{error}</div>}

          <div className="flex gap-2">
            <button className="btn btn-primary" type="submit" disabled={loading}>
              {loading ? '提交中...' : '添加训练数据'}
            </button>
            <button className="btn btn-secondary" type="button" onClick={handleAutoImport} disabled={loading || !form.db_connection_id}>
              <Upload size={14} /> 自动导入 Schema
            </button>
          </div>
        </form>
      </div>

      <div className="card">
        <div className="card-header flex items-center justify-between">
          <span>
            <FileText size={16} style={{ marginRight: '6px', verticalAlign: 'middle' }} />
            训练数据列表 ({trainings.length})
          </span>
        </div>

        {trainings.length === 0 ? (
          <p style={{ textAlign: 'center', padding: '24px', color: '#94a3b8' }}>
            暂无训练数据，请添加 DDL、Schema、文档或 SQL 示例
          </p>
        ) : (
          <div className="training-list">
            {trainings.map((t) => (
              <div key={t.id} className="training-item">
                <div style={{ flex: 1 }}>
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`training-type-badge ${getBadgeClass(t.training_type)}`}>
                      {typeLabels[t.training_type]}
                    </span>
                    <span className="text-sm text-secondary">
                      {new Date(t.created_at).toLocaleString('zh-CN')}
                    </span>
                  </div>
                  {t.training_type === 'sql_example' ? (
                    <>
                      <div style={{ fontSize: '14px', fontWeight: 500, marginBottom: '4px' }}>
                        Q: {t.question}
                      </div>
                      <code style={{ fontSize: '12px', background: '#f1f5f9', padding: '4px 8px', borderRadius: '4px', display: 'block' }}>
                        {t.sql}
                      </code>
                    </>
                  ) : (
                    <div style={{ fontSize: '13px', whiteSpace: 'pre-wrap', color: '#475569' }}>
                      {t.content.length > 200 ? t.content.substring(0, 200) + '...' : t.content}
                    </div>
                  )}
                </div>
                <button
                  className="btn btn-danger btn-sm"
                  onClick={() => handleDelete(t.id)}
                  style={{ flexShrink: 0, marginLeft: '12px' }}
                >
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

export default Training;
