import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Button,
  Tag,
  Progress,
  Descriptions,
  List,
  Space,
  message,
  Row,
  Col,
  Select,
  Divider,
  Empty,
  Modal,
  Checkbox,
} from 'antd';
import {
  ArrowLeftOutlined,
  EditOutlined,
  DownloadOutlined,
  ReloadOutlined,
  FileOutlined,
  PictureOutlined,
  InboxOutlined,
} from '@ant-design/icons';
import { taskApi, outputApi } from '../services/api';
import { TASK_STATUS } from '../constants/elements';
import dayjs from 'dayjs';
import JSZip from 'jszip';

const { Option } = Select;

function TaskDetail() {
  const { taskId } = useParams();
  const navigate = useNavigate();
  const [task, setTask] = useState(null);
  const [loading, setLoading] = useState(false);
  const [outputFormat, setOutputFormat] = useState('json');
  const [downloading, setDownloading] = useState(false);
  const [batchExportVisible, setBatchExportVisible] = useState(false);
  const [selectedFormats, setSelectedFormats] = useState(['json']);
  const [batchExporting, setBatchExporting] = useState(false);
  const intervalRef = useRef(null);

  const fetchTask = async (showLoading = false) => {
    if (showLoading) setLoading(true);
    try {
      const data = await taskApi.get(taskId);
      setTask(data);
    } catch (error) {
      message.error('获取任务详情失败');
    } finally {
      if (showLoading) setLoading(false);
    }
  };

  useEffect(() => {
    fetchTask(true);
  }, [taskId]);

  useEffect(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (task?.status === 'processing' || task?.status === 'pending') {
      intervalRef.current = setInterval(() => fetchTask(false), 2000);
    }
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [taskId, task?.status]);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const blob = await outputApi.get(taskId, outputFormat);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const ext = outputFormat === 'markdown' ? 'md' : outputFormat;
      a.download = task.filename.replace(/\.[^.]+$/, '') + `_output.${ext}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      message.success('下载成功');
    } catch (error) {
      message.error('下载失败');
    } finally {
      setDownloading(false);
    }
  };

  const handleBatchExport = async () => {
    if (selectedFormats.length === 0) {
      message.warning('请至少选择一种导出格式');
      return;
    }

    setBatchExporting(true);
    try {
      const zip = new JSZip();
      const baseName = task.filename.replace(/\.[^.]+$/, '');

      for (const format of selectedFormats) {
        try {
          const blob = await outputApi.get(taskId, format);
          const ext = format === 'markdown' ? 'md' : format;
          const fileName = `${baseName}_output.${ext}`;

          const arrayBuffer = await blob.arrayBuffer();
          const uint8Array = new Uint8Array(arrayBuffer);

          let textContent;
          try {
            const decoder = new TextDecoder('utf-8');
            textContent = decoder.decode(uint8Array);
          } catch {
            textContent = new Blob([uint8Array], { type: blob.type });
          }

          zip.file(fileName, textContent);
        } catch (err) {
          message.warning(`${format.toUpperCase()} 格式导出失败，已跳过`);
        }
      }

      const zipBlob = await zip.generateAsync({ type: 'blob' });
      const url = URL.createObjectURL(zipBlob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${baseName}_outputs.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      message.success('批量导出成功');
      setBatchExportVisible(false);
    } catch (error) {
      message.error('批量导出失败');
    } finally {
      setBatchExporting(false);
    }
  };

  const handleRetry = async () => {
    try {
      await taskApi.retry(taskId);
      message.success('任务已重新提交');
      fetchTask();
    } catch (error) {
      message.error('重试失败');
    }
  };

  if (!task) {
    return <Empty description="任务不存在" />;
  }

  const statusInfo = TASK_STATUS[task.status] || { text: task.status, color: 'default' };
  const progress = task.total_pages > 0
    ? Math.round((task.current_page / task.total_pages) * 100)
    : 0;

  const pages = task.pages || [];

  const formatOptions = [
    { label: 'JSON', value: 'json' },
    { label: 'HTML', value: 'html' },
    { label: 'Markdown', value: 'markdown' },
  ];

  return (
    <div>
      <Card style={{ marginBottom: 16 }}>
        <Space style={{ marginBottom: 16 }}>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>
            返回列表
          </Button>
          {task.status === 'completed' && (
            <Button
              type="primary"
              icon={<EditOutlined />}
              onClick={() => navigate(`/tasks/${taskId}/proofread`)}
            >
              校对编辑
            </Button>
          )}
          {task.status === 'failed' && (
            <Button icon={<ReloadOutlined />} onClick={handleRetry}>
              重试
            </Button>
          )}
        </Space>

        <Descriptions title="任务信息" bordered column={2}>
          <Descriptions.Item label="文件名">{task.filename}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={statusInfo.color}>{statusInfo.text}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="总页数">{task.total_pages || '-'}</Descriptions.Item>
          <Descriptions.Item label="当前处理页">{task.current_page || 0}</Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {dayjs(task.created_at).format('YYYY-MM-DD HH:mm:ss')}
          </Descriptions.Item>
          <Descriptions.Item label="过期时间">
            {task.expires_at ? dayjs(task.expires_at).format('YYYY-MM-DD HH:mm:ss') : '-'}
          </Descriptions.Item>
          {task.error_message && (
            <Descriptions.Item label="错误信息" span={2}>
              <span style={{ color: '#ff4d4f' }}>{task.error_message}</span>
            </Descriptions.Item>
          )}
        </Descriptions>

        <Divider />

        <div style={{ marginBottom: 16 }}>
          <Progress
            percent={progress}
            status={task.status === 'failed' ? 'exception' : task.status === 'completed' ? 'success' : 'active'}
          />
        </div>

        {task.status === 'completed' && (
          <div>
            <Space wrap>
              <span>导出格式:</span>
              <Select
                value={outputFormat}
                onChange={setOutputFormat}
                style={{ width: 150 }}
              >
                <Option value="json">JSON</Option>
                <Option value="html">HTML</Option>
                <Option value="markdown">Markdown</Option>
              </Select>
              <Button
                type="primary"
                icon={<DownloadOutlined />}
                onClick={handleDownload}
                loading={downloading}
              >
                下载结果
              </Button>
              <Button
                icon={<InboxOutlined />}
                onClick={() => {
                  setSelectedFormats(['json']);
                  setBatchExportVisible(true);
                }}
              >
                批量导出
              </Button>
            </Space>
            <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
              提示：批量导出可同时选择多种格式，打包成 ZIP 文件下载。多页结果会合并到同一个输出文件中。
            </div>
          </div>
        )}
      </Card>

      <Card title="页面列表">
        {pages.length === 0 ? (
          <Empty description="暂无页面数据" />
        ) : (
          <List
            grid={{ gutter: 16, xs: 2, sm: 3, md: 4, lg: 6, xl: 8 }}
            dataSource={pages}
            renderItem={(page) => (
              <List.Item>
                <Card
                  hoverable
                  cover={
                    <div
                      style={{
                        height: 150,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        background: '#f5f5f5',
                        overflow: 'hidden',
                      }}
                    >
                      <PictureOutlined style={{ fontSize: 48, color: '#ccc' }} />
                    </div>
                  }
                  onClick={() => navigate(`/tasks/${taskId}/proofread?page=${page.page_number}`)}
                >
                  <Card.Meta
                    title={`第 ${page.page_number} 页`}
                    description={
                      <Space size="small">
                        <Tag color={TASK_STATUS[page.status]?.color || 'default'}>
                          {TASK_STATUS[page.status]?.text || page.status}
                        </Tag>
                        <span style={{ fontSize: 12, color: '#999' }}>
                          {page.elements?.length || 0} 个元素
                        </span>
                      </Space>
                    }
                  />
                </Card>
              </List.Item>
            )}
          />
        )}
      </Card>

      <Modal
        title="批量导出"
        open={batchExportVisible}
        onOk={handleBatchExport}
        onCancel={() => !batchExporting && setBatchExportVisible(false)}
        confirmLoading={batchExporting}
        okText="确认导出并打包下载"
        cancelText="取消"
        width={480}
      >
        <div style={{ marginBottom: 16 }}>
          <p style={{ marginBottom: 12, color: '#666' }}>
            选择要导出的格式（可多选），所有选中格式的文件将打包成 ZIP 文件下载。
          </p>
          <p style={{ marginBottom: 16, color: '#666' }}>
            <FileOutlined style={{ marginRight: 4 }} />
            任务：<strong>{task.filename}</strong>（共 {task.total_pages} 页）
          </p>
          <Checkbox.Group
            value={selectedFormats}
            onChange={(values) => setSelectedFormats(values)}
            style={{ width: '100%' }}
          >
            <Row gutter={[16, 16]}>
              {formatOptions.map((opt) => (
                <Col span={8} key={opt.value}>
                  <div
                    style={{
                      border: selectedFormats.includes(opt.value)
                        ? '2px solid #1890ff'
                        : '1px solid #d9d9d9',
                      borderRadius: 8,
                      padding: 16,
                      textAlign: 'center',
                      cursor: 'pointer',
                      background: selectedFormats.includes(opt.value) ? '#e6f7ff' : '#fff',
                      transition: 'all 0.2s',
                    }}
                    onClick={() => {
                      if (selectedFormats.includes(opt.value)) {
                        setSelectedFormats(selectedFormats.filter((f) => f !== opt.value));
                      } else {
                        setSelectedFormats([...selectedFormats, opt.value]);
                      }
                    }}
                  >
                    <Checkbox
                      checked={selectedFormats.includes(opt.value)}
                      onChange={(e) => e.stopPropagation()}
                      style={{ marginBottom: 8 }}
                    />
                    <div style={{ fontWeight: 'bold', fontSize: 16, marginBottom: 4 }}>
                      {opt.label}
                    </div>
                    <div style={{ fontSize: 12, color: '#999' }}>
                      .{opt.value === 'markdown' ? 'md' : opt.value}
                    </div>
                  </div>
                </Col>
              ))}
            </Row>
          </Checkbox.Group>
        </div>
        <div
          style={{
            padding: 12,
            background: '#f6ffed',
            border: '1px solid #b7eb8f',
            borderRadius: 4,
            fontSize: 12,
            color: '#52c41a',
          }}
        >
          已选择 {selectedFormats.length} 种格式
          {selectedFormats.length > 0 && `：${selectedFormats.map((f) => f.toUpperCase()).join('、')}`}
        </div>
      </Modal>
    </div>
  );
}

export default TaskDetail;
