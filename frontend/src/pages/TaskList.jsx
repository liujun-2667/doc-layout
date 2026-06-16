import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Table,
  Button,
  Upload,
  Modal,
  Tag,
  Progress,
  Space,
  message,
  Popconfirm,
  Statistic,
  Row,
  Col,
} from 'antd';
import {
  UploadOutlined,
  ReloadOutlined,
  EyeOutlined,
  DeleteOutlined,
  FileOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { taskApi } from '../services/api';
import { TASK_STATUS } from '../constants/elements';
import dayjs from 'dayjs';

const { Dragger } = Upload;

function TaskList() {
  const navigate = useNavigate();
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [stats, setStats] = useState({ total: 0, completed: 0, processing: 0, failed: 0 });

  const fetchTasks = useCallback(async () => {
    setLoading(true);
    try {
      const data = await taskApi.list(0, 100);
      setTasks(data.tasks);
      computeStats(data.tasks);
    } catch (error) {
      message.error('获取任务列表失败');
    } finally {
      setLoading(false);
    }
  }, []);

  const computeStats = (taskList) => {
    const stats = {
      total: taskList.length,
      completed: 0,
      processing: 0,
      failed: 0,
      pending: 0,
    };
    taskList.forEach((t) => {
      if (t.status === 'completed') stats.completed++;
      else if (t.status === 'processing') stats.processing++;
      else if (t.status === 'failed') stats.failed++;
      else if (t.status === 'pending') stats.pending++;
    });
    setStats(stats);
  };

  useEffect(() => {
    fetchTasks();
    const interval = setInterval(fetchTasks, 3000);
    return () => clearInterval(interval);
  }, [fetchTasks]);

  const handleUpload = async (file) => {
    setUploading(true);
    setUploadProgress(0);
    try {
      await taskApi.create(file, (progressEvent) => {
        const percent = Math.round((progressEvent.loaded / progressEvent.total) * 100);
        setUploadProgress(percent);
      });
      message.success('上传成功，任务已开始处理');
      fetchTasks();
    } catch (error) {
      message.error(error.response?.data?.detail || '上传失败');
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
    return false;
  };

  const handleRetry = async (taskId) => {
    try {
      await taskApi.retry(taskId);
      message.success('任务已重新提交');
      fetchTasks();
    } catch (error) {
      message.error('重试失败');
    }
  };

  const handleDelete = async (taskId) => {
    try {
      await taskApi.delete(taskId);
      message.success('删除成功');
      fetchTasks();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const columns = [
    {
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
      render: (text, record) => (
        <a onClick={() => navigate(`/tasks/${record.id}`)}>
          <FileOutlined style={{ marginRight: 8 }} />
          {text}
        </a>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status) => {
        const statusInfo = TASK_STATUS[status] || { text: status, color: 'default' };
        return <Tag color={statusInfo.color}>{statusInfo.text}</Tag>;
      },
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      width: 200,
      render: (_, record) => {
        const percent = record.total_pages > 0
          ? Math.round((record.current_page / record.total_pages) * 100)
          : 0;
        return (
          <Progress
            percent={percent}
            size="small"
            status={record.status === 'failed' ? 'exception' : 'active'}
          />
        );
      },
    },
    {
      title: '总页数',
      dataIndex: 'total_pages',
      key: 'total_pages',
      width: 80,
      render: (text) => text || '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (text) => dayjs(text).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/tasks/${record.id}`)}
          >
            查看
          </Button>
          {record.status === 'failed' && (
            <Button
              type="link"
              size="small"
              icon={<SyncOutlined />}
              onClick={() => handleRetry(record.id)}
            >
              重试
            </Button>
          )}
          <Popconfirm
            title="确定删除此任务？"
            onConfirm={() => handleDelete(record.id)}
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总任务数"
              value={stats.total}
              prefix={<FileOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="处理中"
              value={stats.processing + stats.pending}
              valueStyle={{ color: '#1890ff' }}
              prefix={<SyncOutlined spin />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="已完成"
              value={stats.completed}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="失败"
              value={stats.failed}
              valueStyle={{ color: '#ff4d4f' }}
              prefix={<CloseCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title="任务列表"
        extra={
          <Upload
            accept=".pdf,.jpg,.jpeg,.png,.tiff,.tif,.bmp"
            showUploadList={false}
            beforeUpload={handleUpload}
            disabled={uploading}
          >
            <Button type="primary" icon={<UploadOutlined />} loading={uploading}>
              上传文档
            </Button>
          </Upload>
        }
      >
        <Upload.Dragger
          accept=".pdf,.jpg,.jpeg,.png,.tiff,.tif,.bmp"
          showUploadList={false}
          beforeUpload={handleUpload}
          disabled={uploading}
          style={{ marginBottom: 16, padding: '40px 20px' }}
        >
          <p className="ant-upload-drag-icon">
            <UploadOutlined />
          </p>
          <p className="ant-upload-text">
            点击或拖拽文件到此处上传
          </p>
          <p className="ant-upload-hint">
            支持 PDF、JPG、PNG、TIFF 格式，单次最多 50 页
          </p>
          {uploading && (
            <Progress percent={uploadProgress} size="small" status="active" />
          )}
        </Upload.Dragger>

        <Table
          columns={columns}
          dataSource={tasks}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>
    </div>
  );
}

export default TaskList;
