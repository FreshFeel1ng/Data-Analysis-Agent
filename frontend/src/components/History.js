import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ReactEChartsCore from 'echarts-for-react/lib/core';
import * as echarts from 'echarts/core';
import { BarChart, LineChart, PieChart, ScatterChart } from 'echarts/charts';
import { TitleComponent, TooltipComponent, GridComponent, LegendComponent, ToolboxComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { Clock, CheckCircle, XCircle, ChevronDown, ChevronUp, Trash2, Download } from 'lucide-react';
import { api } from '../api/client';

echarts.use([BarChart, LineChart, PieChart, ScatterChart,
  TitleComponent, TooltipComponent, GridComponent, LegendComponent, ToolboxComponent,
  CanvasRenderer]);

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

  const mergeChartData = (option, queryData) => {
    if (!option || !queryData) return option;
    const merge = option.__merge_data__;
    if (!merge) return option;
    const cols = queryData.columns || [];
    const rows = queryData.rows || [];
    if (!cols.length || !rows.length) return option;
    const getColumn = (name) => { const idx = cols.findIndex(c => c === name); return idx >= 0 ? rows.map(r => r[idx]) : []; };
    const merged = { ...option };
    delete merged.__merge_data__;
    if (merge.x_column) merged.xAxis = { ...merged.xAxis, data: getColumn(merge.x_column) };
    if (merge.series_columns && merged.series) merge.series_columns.forEach((colName, i) => { if (merged.series[i]) merged.series[i] = { ...merged.series[i], data: getColumn(colName) }; });
    if (merge.name_column && merge.value_column && merged.series?.[0]) {
      const names = getColumn(merge.name_column), values = getColumn(merge.value_column);
      merged.series[0] = { ...merged.series[0], data: names.map((n, i) => ({ name: String(n), value: Number(values[i]) || 0 })) };
    }
    return merged;
  };

  const getChartOptions = (chartData, queryResult) => {
    if (!chartData) return [];
    try {
      let queryData = null;
      if (queryResult) {
        const parsed = typeof queryResult === 'string' ? JSON.parse(queryResult) : queryResult;
        if (parsed.columns && parsed.rows) queryData = parsed;
      }
      const raw = typeof chartData === 'string' ? JSON.parse(chartData) : chartData;
      const items = Array.isArray(raw) ? raw : [raw];
      return items.map(item => {
        if (typeof item === 'string') item = JSON.parse(item);
        if (item.echarts_option) return mergeChartData(item.echarts_option, queryData);
        if (item.image_base64) return item.image_base64;
        return null;
      }).filter(Boolean);
    } catch { return []; }
  };

  const downloadChart = (option) => {
    if (typeof option === 'string') {
      const byteChars = atob(option);
      const bytes = new Uint8Array(byteChars.length);
      for (let i = 0; i < byteChars.length; i++) bytes[i] = byteChars.charCodeAt(i);
      const blob = new Blob([bytes], { type: 'image/png' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `chart_${new Date().toISOString().slice(0, 10)}.png`;
      a.click(); URL.revokeObjectURL(url);
    } else {
      const chartEl = document.querySelector('.echarts-for-react canvas');
      if (chartEl) {
        const a = document.createElement('a');
        a.href = chartEl.toDataURL('image/png');
        a.download = `chart_${new Date().toISOString().slice(0, 10)}.png`;
        a.click();
      }
    }
  };

  const downloadCsv = (cols, rows) => {
    const BOM = '\uFEFF';
    const csv = BOM + [cols.join(','), ...rows.map(r => r.map(c => `"${c ?? ''}"`).join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `data_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click(); URL.revokeObjectURL(url);
  };

  const downloadReport = (record) => {
    const md = ['# 数据分析报告', `时间: ${new Date().toLocaleString('zh-CN')}`, '', `问题: ${record.question}`, '',
      record.sql ? `## SQL\n\`\`\`sql\n${record.sql}\n\`\`\`` : '',
      '## 分析结果', record.explanation || ''].filter(Boolean).join('\n\n');
    const blob = new Blob([md], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `report_${new Date().toISOString().slice(0, 10)}.md`;
    a.click(); URL.revokeObjectURL(url);
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
            const chartOptions = getChartOptions(r.chart_data, r.result_json);
            const hasDetail = r.sql || resultData || chartOptions.length > 0 || r.explanation;

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
                        <div className="flex items-center justify-between" style={{ marginBottom: '6px' }}>
                          <span style={{ fontSize: '13px', fontWeight: 600, color: '#64748b' }}>SQL</span>
                        </div>
                        <pre style={{ background: '#1e293b', color: '#e2e8f0', padding: '12px', borderRadius: '8px', fontSize: '12px', overflowX: 'auto', whiteSpace: 'pre-wrap' }}>
                          {r.sql}
                        </pre>
                      </div>
                    )}

                    {chartOptions.length > 0 && chartOptions.map((option, idx) => (
                      <div key={idx} style={{ marginBottom: '12px' }}>
                        <div className="flex items-center justify-between" style={{ marginBottom: '6px' }}>
                          <span style={{ fontSize: '13px', fontWeight: 600, color: '#64748b' }}>
                            {chartOptions.length > 1 ? `图表 ${idx + 1}` : '图表'}
                          </span>
                          <button className="btn btn-sm btn-secondary" onClick={() => downloadChart(option)}>
                            <Download size={14} /> 下载 PNG
                          </button>
                        </div>
                        {typeof option === 'string' ? (
                          <img src={`data:image/png;base64,${option}`} alt="Chart"
                            style={{ maxWidth: '100%', maxHeight: '400px', borderRadius: '8px' }} />
                        ) : (
                          <ReactEChartsCore
                            echarts={echarts}
                            option={option}
                            style={{ width: '100%', height: '350px' }}
                            notMerge={true}
                          />
                        )}
                      </div>
                    ))}

                    {resultData && resultData.columns && (
                      <div style={{ marginBottom: '12px' }}>
                        <div className="flex items-center justify-between" style={{ marginBottom: '6px' }}>
                          <span style={{ fontSize: '13px', fontWeight: 600, color: '#64748b' }}>数据 ({resultData.row_count} 行)</span>
                          <button className="btn btn-sm btn-secondary" onClick={() => downloadCsv(resultData.columns, resultData.rows || [])}>
                            <Download size={14} /> 下载 CSV
                          </button>
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
                        <div className="flex items-center justify-between" style={{ marginBottom: '6px' }}>
                          <span style={{ fontSize: '13px', fontWeight: 600, color: '#64748b' }}>分析结果</span>
                          <button className="btn btn-sm btn-secondary" onClick={() => downloadReport(r)}>
                            <Download size={14} /> 下载报告
                          </button>
                        </div>
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
