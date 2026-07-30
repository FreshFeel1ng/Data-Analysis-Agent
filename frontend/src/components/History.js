import React, { useState, useEffect } from 'react';
import { Clock, CheckCircle, XCircle, Search } from 'lucide-react';
import { api } from '../api/client';

function History() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const { data } = await api.getQueryHistory({ limit: 100 });
      setRecords(data);
    } catch (err) {
      console.error('Failed to load history:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (ts) => {
    if (!ts) return '';
    const d = new Date(ts);
    return d.toLocaleString('zh-CN');
  };

  return (
    <div>
      <div className="page-header">
        <h2>历史记录</h2>
        <p>查看你的查询历史和分析结果</p>
      </div>

      {loading ? (
        <div className="loading"><span className="spinner" />加载中...</div>
      ) : records.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '48px', color: '#94a3b8' }}>
          <Search size={32} style={{ marginBottom: '8px' }} />
          <p>暂无查询记录</p>
          <p className="text-sm" style={{ marginTop: '4px' }}>开始使用 SQL 查询功能，这里将显示你的历史</p>
        </div>
      ) : (
        <div>
          {records.map((r) => (
            <div key={r.id} className="history-item">
              <div className="flex items-center gap-2">
                {r.success ? (
                  <CheckCircle size={16} color="#16a34a" />
                ) : (
                  <XCircle size={16} color="#dc2626" />
                )}
                <span className="history-question">{r.detail}</span>
              </div>
              <div className="history-meta">
                {r.params?.db_name && <span>数据源: {r.params.db_name} · </span>}
                {r.params?.sql && (
                  <code style={{ background: '#f1f5f9', padding: '2px 6px', borderRadius: '4px', fontSize: '12px' }}>
                    {r.params.sql.length > 80 ? r.params.sql.substring(0, 80) + '...' : r.params.sql}
                  </code>
                )}
                <span style={{ marginLeft: '8px' }}>{formatTime(r.created_at)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default History;
