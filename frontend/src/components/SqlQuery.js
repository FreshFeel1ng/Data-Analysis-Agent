import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Send, Loader2, Database, ChevronDown, BarChart3 } from 'lucide-react';
import { api } from '../api/client';

function SqlQuery() {
  const [question, setQuestion] = useState('');
  const [dbConnId, setDbConnId] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [connections, setConnections] = useState([]);

  // Load connections on mount
  React.useEffect(() => {
    api.listConnections()
      .then(({ data }) => {
        setConnections(data);
        if (data.length > 0) setDbConnId(String(data[0].id));
      })
      .catch(() => {});
  }, []);

  const handleAsk = async () => {
    if (!question.trim()) return;
    if (!dbConnId) {
      setError('请先选择一个数据源');
      return;
    }
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const { data } = await api.ask({
        question: question.trim(),
        db_connection_id: parseInt(dbConnId),
      });
      setResult(data);
    } catch (err) {
      setError(err.response?.data?.detail || '查询失败');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleAsk();
    }
  };

  const renderQueryResult = () => {
    if (!result) return null;

    let dataRows = [];
    let dataCols = [];
    if (result.result) {
      try {
        const parsed = typeof result.result === 'string'
          ? JSON.parse(result.result)
          : result.result;
        dataCols = parsed.columns || [];
        dataRows = parsed.rows || [];
      } catch (e) {}
    }

    let chartBase64 = null;
    if (result.chart_data) {
      try {
        const chart = typeof result.chart_data === 'string'
          ? JSON.parse(result.chart_data)
          : result.chart_data;
        chartBase64 = chart.image_base64;
      } catch (e) {}
    }

    return (
      <div className="result-container">
        {result.sql && (
          <div>
            <div style={{ fontSize: '13px', fontWeight: 600, marginBottom: '6px', color: '#64748b' }}>
              生成的 SQL
            </div>
            <div className="sql-block">{result.sql}</div>
          </div>
        )}

        {chartBase64 && (
          <div className="chart-container">
            <img src={`data:image/png;base64,${chartBase64}`} alt="Chart" />
          </div>
        )}

        {dataCols.length > 0 && dataRows.length > 0 && (
          <div className="card">
            <div className="card-header">
              <Database size={16} style={{ marginRight: '6px', verticalAlign: 'middle' }} />
              查询结果 ({dataRows.length} 行)
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    {dataCols.map((col, i) => (
                      <th key={i}>{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {dataRows.slice(0, 100).map((row, i) => (
                    <tr key={i}>
                      {row.map((cell, j) => (
                        <td key={j}>{cell === null ? (
                          <span style={{ color: '#94a3b8', fontStyle: 'italic' }}>NULL</span>
                        ) : String(cell)}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              {dataRows.length > 100 && (
                <p style={{ padding: '8px 12px', fontSize: '13px', color: '#64748b' }}>
                  仅显示前 100 行，共 {dataRows.length} 行
                </p>
              )}
            </div>
          </div>
        )}

        {result.explanation && (
          <div className="card">
            <div className="card-header">
              <BarChart3 size={16} style={{ marginRight: '6px', verticalAlign: 'middle' }} />
              分析结果
            </div>
            <ReactMarkdown
              components={{
                p: ({ children }) => <p style={{ fontSize: '14px', lineHeight: '1.7', marginBottom: '8px' }}>{children}</p>,
                code: ({ children }) => (
                  <code style={{ background: '#f1f5f9', padding: '2px 6px', borderRadius: '4px', fontSize: '13px' }}>
                    {children}
                  </code>
                ),
              }}
            >
              {result.explanation}
            </ReactMarkdown>
          </div>
        )}

        {!result.success && (
          <div className="error-msg">{result.error || '查询执行失败'}</div>
        )}
      </div>
    );
  };

  return (
    <div>
      <div className="page-header">
        <h2>SQL 智能查询</h2>
        <p>用自然语言描述你的数据分析需求，AI 将自动生成 SQL 并执行</p>
      </div>

      <div className="card">
        <div style={{ marginBottom: '12px' }}>
          <label style={{ fontSize: '13px', fontWeight: 500, display: 'block', marginBottom: '6px' }}>
            选择数据源
          </label>
          <select
            className="select"
            value={dbConnId}
            onChange={(e) => setDbConnId(e.target.value)}
            style={{ maxWidth: '300px' }}
          >
            <option value="">-- 选择数据源 --</option>
            {connections.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} ({c.db_type})
              </option>
            ))}
          </select>
          {connections.length === 0 && (
            <p style={{ fontSize: '12px', color: '#f59e0b', marginTop: '4px' }}>
              暂无数据源，请先在"数据源"页面添加
            </p>
          )}
        </div>

        <div className="query-input-area">
          <textarea
            className="textarea"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="例如：查询上个月销售额最高的10个产品；分析用户注册趋势..."
            rows={2}
          />
          <button
            className="btn btn-primary"
            onClick={handleAsk}
            disabled={loading || !question.trim() || !dbConnId}
            style={{ alignSelf: 'flex-end', height: '60px', minWidth: '100px' }}
          >
            {loading ? <Loader2 size={18} className="spin-icon" /> : <Send size={18} />}
            {loading ? '分析中' : '查询'}
          </button>
        </div>

        {error && <div className="error-msg mt-3">{error}</div>}
      </div>

      {loading && (
        <div className="loading">
          <span className="spinner" />
          AI 正在分析你的问题，生成 SQL 并执行查询...
        </div>
      )}

      {renderQueryResult()}
    </div>
  );
}

export default SqlQuery;
