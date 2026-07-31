import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Clock, CheckCircle, XCircle, ChevronDown, ChevronUp, Trash2, Copy, Download } from 'lucide-react';
import { api } from '../api/client';

function History() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(null);

  useEffect(() => { loadHistory(); }, []);

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

  const handleDelete = async (id) => {
    if (!window.confirm('确认删除此记录？')) return;
    try {
      await fetch(`/api/history/queries/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      setRecords(records.filter(r => r.id !== id));
    } catch (err) {
      console.error('Delete failed:', err);
    }
  };

  const toggleExpand = (id) => setExpanded(expanded === id ? null : id);

  const formatTime = (ts) => ts ? new Date(ts).toLocaleString('zh-CN') : '';

  const parseResult = (jsonStr) => {
    try { return JSON.parse(jsonStr); } catch { return null; }
  };

  const getChartBase64 = (chartData) => {
    if (!chartData) return null;
    try {
      const parsed = typeof chartData === 'string' ? JSON.parse(chartData) : chartData;
      return parsed.image_base64;
    } catch { return null; }
  };

  return (
    <div>
      <div className="page-header">
        <h2>历史记录</h2>
        <p>查看完整的查询历史和分析结果，点击展开查看详情</p>
      </div>

      {loading ? (
        <div className="loading"><span className="spinner" />加载中...</div>
      ) : records.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '48px', color: '#94a3b8' }}>
          <Clock size={32} style={{ marginBottom: '8px' }} />
          <p>暂无查询记录</p>
        </div>
      ) : (
        <div>
          {records.map((r) => {
            const isOpen = expanded === r.id;
            const resultData = parseResult(r.result_json);
            const chartB64 = getChartBase64(r.chart_data);
            const hasDetail = r.sql || resultData || chartB64 || r.explanation;

            return (
              <div key={r.id} className="card" style={{ padding: '16px' }}>
                {/* Summary Row */}
                <div style={{ cursor: 'pointer' }} onClick={() => toggleExpand(r.id)}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2" style={{ flex: 1 }}>
                      {r.success ? <CheckCircle size={16} color="#16a34a" /> : <XCircle size={16} color="#dc2626" />}
                      <span style={{ fontWeight: 500, fontSize: '14px' }}>{r.question}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {r.db_name && (
                        <span style={{ fontSize: '12px', background: '#dbeafe', color: '#2563eb', padding: '2px 8px', borderRadius: '10px' }}>
                          {r.db_name}
                        </span>
                      )}
                      <span style={{ fontSize: '12px', color: '#94a3b8' }}>{formatTime(r.created_at)}</span>
                      <button className="btn btn-danger btn-sm" onClick={(e) => { e.stopPropagation(); handleDelete(r.id); }}>
                        <Trash2 size={14} />
                      </button>
                      {hasDetail && (isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />)}
                    </div>
                  </div>
                  {!isOpen && r.sql && (
                    <div style={{ marginTop: '6px' }}>
                      <code style={{ fontSize: '12px', background: '#f1f5f9', padding: '2px 6px', borderRadius: '4px', color: '#475569' }}>
                        {r.sql.length > 100 ? r.sql.substring(0, 100) + '...' : r.sql}
                      </code>
                    </div>
                  )}
                </div>

                {/* Expanded Detail */}
                {isOpen && hasDetail && (
                  <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid #e2e8f0' }}>
                    {r.sql && (
                      <div style={{ marginBottom: '12px' }}>
                        <div style={{ fontSize: '13px', fontWeight: 600, marginBottom: '6px', color: '#64748b' }}>SQL</div>
                        <pre style={{ background: '#1e293b', color: '#e2e8f0', padding: '12px', borderRadius: '8px', fontSize: '12px', overflowX: 'auto', whiteSpace: 'pre-wrap' }}>
                          {r.sql}
                        </pre>
                      </div>
                    )}

                    {chartB64 && (
                      <div style={{ marginBottom: '12px', textAlign: 'center' }}>
                        <div style={{ fontSize: '13px', fontWeight: 600, marginBottom: '6px', color: '#64748b', textAlign: 'left' }}>图表</div>
                        <img src={`data:image/png;base64,${chartB64}`} alt="Chart"
                          style={{ maxWidth: '100%', maxHeight: '400px', borderRadius: '8px' }} />
                      </div>
                    )}

                    {resultData && resultData.columns && (
                      <div style={{ marginBottom: '12px' }}>
                        <div style={{ fontSize: '13px', fontWeight: 600, marginBottom: '6px', color: '#64748b' }}>
                          数据 ({resultData.row_count} 行)
                        </div>
                        <div style={{ overflowX: 'auto', maxHeight: '300px', overflowY: 'auto' }}>
                          <table className="data-table" style={{ fontSize: '12px' }}>
                            <thead>
                              <tr>{resultData.columns.map((col, i) => <th key={i}>{col}</th>)}</tr>
                            </thead>
                            <tbody>
                              {(resultData.rows || []).slice(0, 20).map((row, i) => (
                                <tr key={i}>{row.map((cell, j) => <td key={j}>{cell === null ? <span style={{ color: '#94a3b8' }}>NULL</span> : String(cell)}</td>)}</tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}

                    {r.explanation && (
                      <div>
                        <div style={{ fontSize: '13px', fontWeight: 600, marginBottom: '6px', color: '#64748b' }}>分析结果</div>
                        <div style={{ fontSize: '14px', lineHeight: '1.7' }}>
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {r.explanation}
                          </ReactMarkdown>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default History;
