import React, { useState, useCallback, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ReactEChartsCore from 'echarts-for-react/lib/core';
import * as echarts from 'echarts/core';
import { BarChart, LineChart, PieChart, ScatterChart } from 'echarts/charts';
import { TitleComponent, TooltipComponent, GridComponent, LegendComponent, ToolboxComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import {
  Send, Loader2, Database, BarChart3,
  Download, FileDown, Copy, Check
} from 'lucide-react';
import { api } from '../api/client';

echarts.use([BarChart, LineChart, PieChart, ScatterChart,
  TitleComponent, TooltipComponent, GridComponent, LegendComponent, ToolboxComponent,
  CanvasRenderer]);

function SqlQuery() {
  const [question, setQuestion] = useState('');
  const [dbConnId, setDbConnId] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [connections, setConnections] = useState([]);
  const [copied, setCopied] = useState(false);

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
    if (!dbConnId) { setError('请先选择一个数据源'); return; }
    setLoading(true); setError(''); setResult(null);
    try {
      const { data } = await api.ask({ question: question.trim(), db_connection_id: parseInt(dbConnId) });
      setResult(data);
    } catch (err) {
      setError(err.response?.data?.detail || '查询失败');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleAsk(); }
  };

  const downloadFile = useCallback((content, filename, mimeType = 'text/plain') => {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }, []);

  const chartRef = useRef(null);

  const downloadChart = useCallback((option) => {
    if (typeof option === 'string') {
      // Legacy base64
      const byteChars = atob(option);
      const bytes = new Uint8Array(byteChars.length);
      for (let i = 0; i < byteChars.length; i++) bytes[i] = byteChars.charCodeAt(i);
      const blob = new Blob([bytes], { type: 'image/png' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `chart_${new Date().toISOString().slice(0, 10)}.png`;
      a.click(); URL.revokeObjectURL(url);
    } else {
      // ECharts: export via canvas
      const chartEl = document.querySelector('.echarts-for-react canvas');
      if (chartEl) {
        const a = document.createElement('a');
        a.href = chartEl.toDataURL('image/png');
        a.download = `chart_${new Date().toISOString().slice(0, 10)}.png`;
        a.click();
      }
    }
  }, []);

  const downloadCsv = useCallback((cols, rows) => {
    const BOM = '\uFEFF';
    const csv = BOM + [cols.join(','), ...rows.map(r => r.map(c => `"${c ?? ''}"`).join(','))].join('\n');
    downloadFile(csv, `data_${new Date().toISOString().slice(0, 10)}.csv`, 'text/csv;charset=utf-8');
  }, [downloadFile]);

  const downloadReport = useCallback((text, sql) => {
    const md = [
      `# 数据分析报告`,
      `生成时间: ${new Date().toLocaleString('zh-CN')}`,
      `问题: ${question}`,
      '',
      sql ? `## SQL\n\`\`\`sql\n${sql}\n\`\`\`` : '',
      '## 分析结果',
      text,
    ].filter(Boolean).join('\n\n');
    downloadFile(md, `report_${new Date().toISOString().slice(0, 10)}.md`, 'text/markdown');
  }, [question, downloadFile]);

  const copySQL = useCallback((sql) => {
    navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, []);

  const renderQueryResult = () => {
    if (!result) return null;

    let dataRows = [], dataCols = [];
    if (result.result) {
      try {
        const parsed = typeof result.result === 'string' ? JSON.parse(result.result) : result.result;
        dataCols = parsed.columns || [];
        dataRows = parsed.rows || [];
      } catch (e) {}
    }

    let chartOptions = [];
    if (result.chart_data) {
      try {
        const raw = typeof result.chart_data === 'string' ? JSON.parse(result.chart_data) : result.chart_data;
        // Support both array and single object
        const items = Array.isArray(raw) ? raw : [raw];
        chartOptions = items.map(item => {
          if (typeof item === 'string') item = JSON.parse(item);
          if (item.echarts_option) return item.echarts_option;
          if (item.image_base64) return item.image_base64; // legacy
          return null;
        }).filter(Boolean);
      } catch (e) {}
    }

    return (
      <div className="result-container">
        {/* SQL Block */}
        {result.sql && (
          <div>
            <div className="flex items-center justify-between" style={{ marginBottom: '6px' }}>
              <span style={{ fontSize: '13px', fontWeight: 600, color: '#64748b' }}>生成的 SQL</span>
              <button className="btn btn-sm btn-secondary" onClick={() => copySQL(result.sql)}>
                {copied ? <Check size={14} /> : <Copy size={14} />}
                {copied ? '已复制' : '复制'}
              </button>
            </div>
            <div className="sql-block">{result.sql}</div>
          </div>
        )}

        {/* Data Table */}
        {dataCols.length > 0 && dataRows.length > 0 && (
          <div className="card">
            <div className="card-header flex items-center justify-between">
              <span><Database size={16} style={{ marginRight: '6px', verticalAlign: 'middle' }} />查询结果 ({dataRows.length} 行)</span>
              <button className="btn btn-sm btn-secondary" onClick={() => downloadCsv(dataCols, dataRows)}>
                <FileDown size={14} /> 下载 CSV
              </button>
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table className="data-table">
                <thead><tr>{dataCols.map((col, i) => <th key={i}>{col}</th>)}</tr></thead>
                <tbody>
                  {dataRows.slice(0, 100).map((row, i) => (
                    <tr key={i}>
                      {row.map((cell, j) => (
                        <td key={j}>{cell === null ? <span style={{ color: '#94a3b8', fontStyle: 'italic' }}>NULL</span> : String(cell)}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              {dataRows.length > 100 && <p style={{ padding: '8px 12px', fontSize: '13px', color: '#64748b' }}>仅显示前 100 行，共 {dataRows.length} 行</p>}
            </div>
          </div>
        )}

        {/* Charts */}
        {chartOptions.length > 0 && chartOptions.map((option, idx) => (
          <div className="card" key={idx}>
            <div className="flex items-center justify-between" style={{ marginBottom: '12px' }}>
              <span style={{ fontSize: '15px', fontWeight: 600 }}>
                {chartOptions.length > 1 ? `图表 ${idx + 1}` : '图表'}
              </span>
              <button className="btn btn-sm btn-secondary" onClick={() => downloadChart(option)}>
                <Download size={14} /> 下载 PNG
              </button>
            </div>
            {typeof option === 'string' ? (
              <div className="chart-container">
                <img src={`data:image/png;base64,${option}`} alt="Chart" />
              </div>
            ) : (
              <ReactEChartsCore
                echarts={echarts}
                option={option}
                style={{ width: '100%', height: '400px' }}
                notMerge={true}
              />
            )}
          </div>
        ))}

        {/* Analysis */}
        {result.explanation && (
          <div className="card">
            <div className="card-header flex items-center justify-between">
              <span><BarChart3 size={16} style={{ marginRight: '6px', verticalAlign: 'middle' }} />分析结果</span>
              <button className="btn btn-sm btn-secondary" onClick={() => downloadReport(result.explanation, result.sql)}>
                <Download size={14} /> 下载报告
              </button>
            </div>
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                p: ({ children }) => <p style={{ fontSize: '14px', lineHeight: '1.7', marginBottom: '8px' }}>{children}</p>,
                code: ({ className, children, ...props }) => {
                  const isInline = !className;
                  return isInline ? (
                    <code style={{ background: '#f1f5f9', padding: '2px 6px', borderRadius: '4px', fontSize: '13px' }}>{children}</code>
                  ) : (
                    <pre className="sql-block" style={{ margin: '12px 0', padding: '12px 16px' }}><code className={className} {...props}>{children}</code></pre>
                  );
                },
                table: ({ children }) => <div style={{ overflowX: 'auto', margin: '12px 0' }}><table className="data-table">{children}</table></div>,
                th: ({ children }) => <th>{children}</th>,
                td: ({ children }) => <td>{children}</td>,
              }}
            >
              {result.explanation}
            </ReactMarkdown>
          </div>
        )}

        {!result.success && <div className="error-msg">{result.error || '查询执行失败'}</div>}
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
          <label style={{ fontSize: '13px', fontWeight: 500, display: 'block', marginBottom: '6px' }}>选择数据源</label>
          <select className="select" value={dbConnId} onChange={(e) => setDbConnId(e.target.value)} style={{ maxWidth: '300px' }}>
            <option value="">-- 选择数据源 --</option>
            {connections.map((c) => <option key={c.id} value={c.id}>{c.name} ({c.db_type})</option>)}
          </select>
          {connections.length === 0 && <p style={{ fontSize: '12px', color: '#f59e0b', marginTop: '4px' }}>暂无数据源，请先在"数据源"页面添加</p>}
        </div>
        <div className="query-input-area">
          <textarea className="textarea" value={question} onChange={(e) => setQuestion(e.target.value)} onKeyDown={handleKeyDown}
            placeholder="例如：查询各季度销量变化，画出柱形图..." rows={2} />
          <button className="btn btn-primary" onClick={handleAsk} disabled={loading || !question.trim() || !dbConnId}
            style={{ alignSelf: 'flex-end', height: '60px', minWidth: '100px' }}>
            {loading ? <Loader2 size={18} /> : <Send size={18} />}
            {loading ? '分析中' : '查询'}
          </button>
        </div>
        {error && <div className="error-msg mt-3">{error}</div>}
      </div>

      {loading && (<div className="loading"><span className="spinner" />AI 正在分析你的问题...</div>)}
      {renderQueryResult()}
    </div>
  );
}

export default SqlQuery;
