import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Row,
  Col,
  Tag,
  Button,
  Space,
  Typography,
  Form,
  Input,
  Select,
  Descriptions,
  List,
  Tooltip,
  Popconfirm,
  Modal,
  message,
  Divider,
  Empty,
  Statistic,
} from 'antd';
import {
  ArrowLeftOutlined,
  EditOutlined,
  SaveOutlined,
  RollbackOutlined,
  HistoryOutlined,
  FireOutlined,
  FileTextOutlined,
  DeleteOutlined,
  CloseOutlined,
  CalendarOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { templateApi } from '../services/api';
import { ELEMENT_COLORS, getElementColor } from '../constants/elements';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;
const { TextArea } = Input;

const DOCUMENT_TYPES = [
  { value: '论文', label: '论文', color: 'blue' },
  { value: '报告', label: '报告', color: 'purple' },
  { value: '发票', label: '发票', color: 'green' },
  { value: '合同', label: '合同', color: 'orange' },
  { value: '简历', label: '简历', color: 'cyan' },
];

function PagePreview({ page, pageIndex }) {
  const viewBoxWidth = 300;
  const viewBoxHeight = Math.round((page.height / (page.width || 1000)) * 300) || 424;

  if (!page.elements || page.elements.length === 0) {
    return (
      <div
        style={{
          width: '100%',
          height: viewBoxHeight,
          background: '#f5f5f5',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderRadius: 4,
        }}
      >
        <FileTextOutlined style={{ fontSize: 32, color: '#ccc' }} />
      </div>
    );
  }

  return (
    <svg
      viewBox={`0 0 ${viewBoxWidth} ${viewBoxHeight}`}
      style={{
        width: '100%',
        height: viewBoxHeight,
        background: '#fafafa',
        borderRadius: 4,
      }}
    >
      <rect
        x="1"
        y="1"
        width={viewBoxWidth - 2}
        height={viewBoxHeight - 2}
        fill="none"
        stroke="#d9d9d9"
        strokeWidth="1"
        rx="2"
      />
      {page.elements.map((elem) => {
        const color = getElementColor(elem.element_type);
        const x = elem.rel_x * viewBoxWidth;
        const y = elem.rel_y * viewBoxHeight;
        const w = elem.rel_width * viewBoxWidth;
        const h = elem.rel_height * viewBoxHeight;
        return (
          <g key={elem.id}>
            <rect
              x={x}
              y={y}
              width={Math.max(w, 3)}
              height={Math.max(h, 3)}
              fill={color.bg}
              stroke={color.border}
              strokeWidth="1"
              rx="2"
            />
            <text
              x={x + w / 2}
              y={y + h / 2}
              textAnchor="middle"
              dominantBaseline="middle"
              fontSize="8"
              fill={color.border}
              fontWeight="bold"
            >
              {elem.reading_order}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function TemplateDetail() {
  const { templateId } = useParams();
  const navigate = useNavigate();
  const [template, setTemplate] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [form] = Form.useForm();
  const [versions, setVersions] = useState([]);
  const [showVersions, setShowVersions] = useState(false);

  const fetchTemplate = async () => {
    setLoading(true);
    try {
      const data = await templateApi.get(templateId);
      setTemplate(data);
      form.setFieldsValue({
        name: data.name,
        document_types: data.document_types || [],
        description: data.description || '',
      });
    } catch (error) {
      message.error('加载模板详情失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchVersions = async () => {
    try {
      const data = await templateApi.listVersions(templateId);
      setVersions(data || []);
    } catch (error) {
      message.error('加载版本历史失败');
    }
  };

  useEffect(() => {
    fetchTemplate();
    fetchVersions();
  }, [templateId]);

  const handleSave = async (values) => {
    try {
      const updated = await templateApi.update(templateId, values);
      setTemplate(updated);
      setEditing(false);
      message.success('保存成功');
    } catch (error) {
      if (error.response?.status === 409) {
        message.error('已存在同名模板');
      } else {
        message.error('保存失败');
      }
    }
  };

  const handleRollback = async (versionId) => {
    Modal.confirm({
      title: '确认回滚',
      content: '确定要回滚到此版本吗?当前版本将被保存为历史版本。',
      onOk: async () => {
        try {
          const updated = await templateApi.rollbackVersion(templateId, versionId);
          setTemplate(updated);
          fetchVersions();
          setShowVersions(false);
          message.success('回滚成功');
        } catch (error) {
          message.error('回滚失败');
        }
      },
    });
  };

  const handleDelete = async () => {
    try {
      await templateApi.delete(templateId);
      message.success('模板已删除');
      navigate('/templates');
    } catch (error) {
      message.error('删除失败');
    }
  };

  const sortedPages = [...(template?.pages || [])].sort(
    (a, b) => a.page_number - b.page_number
  );

  const totalElements = sortedPages.reduce(
    (sum, p) => sum + (p.elements?.length || 0),
    0
  );

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 24,
        }}
      >
        <Space>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/templates')}
          >
            返回列表
          </Button>
          <Title level={3} style={{ margin: 0 }}>
            模板详情
          </Title>
        </Space>
        <Space>
          <Button
            icon={<HistoryOutlined />}
            onClick={() => {
              setShowVersions(true);
              fetchVersions();
            }}
          >
            版本历史
          </Button>
          <Popconfirm
            title="确定删除此模板吗?"
            onConfirm={handleDelete}
            okText="删除"
            cancelText="取消"
            okType="danger"
          >
            <Button danger icon={<DeleteOutlined />}>
              删除模板
            </Button>
          </Popconfirm>
        </Space>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card title="基本信息" loading={loading}>
            {!editing && template ? (
              <Space direction="vertical" style={{ width: '100%' }}>
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="模板名称">
                    {template.name}
                  </Descriptions.Item>
                  <Descriptions.Item label="适用类型">
                    <Space wrap>
                      {(template.document_types || []).map((type) => {
                        const typeInfo = DOCUMENT_TYPES.find(
                          (t) => t.value === type
                        );
                        return (
                          <Tag key={type} color={typeInfo?.color || 'default'}>
                            {type}
                          </Tag>
                        );
                      })}
                    </Space>
                  </Descriptions.Item>
                  <Descriptions.Item label="备注说明">
                    {template.description || '无'}
                  </Descriptions.Item>
                </Descriptions>
                <Divider style={{ margin: '12px 0' }} />
                <Row gutter={16}>
                  <Col span={12}>
                    <Statistic
                      title="匹配次数"
                      value={template.match_count || 0}
                      prefix={<FireOutlined style={{ color: '#fa8c16' }} />}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="页数"
                      value={sortedPages.length}
                      prefix={<FileTextOutlined style={{ color: '#1890ff' }} />}
                    />
                  </Col>
                </Row>
                <Divider style={{ margin: '12px 0' }} />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  <CalendarOutlined style={{ marginRight: 4 }} />
                  创建时间: {dayjs(template.created_at).format('YYYY-MM-DD HH:mm')}
                </Text>
                {template.updated_at && (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    <br />
                    更新时间: {dayjs(template.updated_at).format('YYYY-MM-DD HH:mm')}
                  </Text>
                )}
                <Divider style={{ margin: '12px 0' }} />
                <Button
                  type="primary"
                  icon={<EditOutlined />}
                  onClick={() => setEditing(true)}
                >
                  编辑信息
                </Button>
              </Space>
            ) : (
              <Form
                form={form}
                layout="vertical"
                onFinish={handleSave}
              >
                <Form.Item
                  label="模板名称"
                  name="name"
                  rules={[{ required: true, message: '请输入模板名称' }]}
                >
                  <Input placeholder="请输入模板名称" />
                </Form.Item>
                <Form.Item
                  label="适用文档类型(可多选)"
                  name="document_types"
                  rules={[{ required: true, message: '请选择至少一种文档类型' }]}
                >
                  <Select mode="multiple" placeholder="选择适用的文档类型">
                    {DOCUMENT_TYPES.map((t) => (
                      <Option key={t.value} value={t.value}>
                        {t.label}
                      </Option>
                    ))}
                  </Select>
                </Form.Item>
                <Form.Item label="备注说明" name="description">
                  <TextArea rows={4} placeholder="可选:输入模板的备注说明" />
                </Form.Item>
                <Space>
                  <Button type="primary" icon={<SaveOutlined />} htmlType="submit">
                    保存
                  </Button>
                  <Button
                    icon={<CloseOutlined />}
                    onClick={() => {
                      setEditing(false);
                      form.resetFields();
                      if (template) {
                        form.setFieldsValue({
                          name: template.name,
                          document_types: template.document_types || [],
                          description: template.description || '',
                        });
                      }
                    }}
                  >
                    取消
                  </Button>
                </Space>
              </Form>
            )}
          </Card>
        </Col>

        <Col xs={24} md={16}>
          <Card
            title={
              <Space>
                <span>版面结构预览</span>
                <Tag color="blue">{totalElements} 个元素</Tag>
              </Space>
            }
            loading={loading}
          >
            {sortedPages.length === 0 ? (
              <Empty description="此模板暂无版面数据" />
            ) : (
              <Row gutter={[16, 16]}>
                {sortedPages.map((page, idx) => (
                  <Col xs={24} sm={12} lg={8} key={page.id}>
                    <Card
                      size="small"
                      title={
                        <Space>
                          <span>第 {page.page_number} 页</span>
                          {page.is_first_page && (
                            <Tag color="gold" size="small">
                              首页
                            </Tag>
                          )}
                        </Space>
                      }
                    >
                      <PagePreview page={page} pageIndex={idx} />
                      <div
                        style={{
                          marginTop: 8,
                          fontSize: 12,
                          color: '#666',
                          textAlign: 'center',
                        }}
                      >
                        {page.elements?.length || 0} 个元素 | {page.width}×{page.height}
                      </div>
                    </Card>
                  </Col>
                ))}
              </Row>
            )}
          </Card>
        </Col>
      </Row>

      <Modal
        title={
          <Space>
            <HistoryOutlined />
            版本历史
          </Space>
        }
        open={showVersions}
        onCancel={() => setShowVersions(false)}
        width={720}
        footer={[
          <Button key="close" onClick={() => setShowVersions(false)}>
            关闭
          </Button>,
        ]}
      >
        {versions.length === 0 ? (
          <Empty description="暂无历史版本" />
        ) : (
          <List
            itemLayout="horizontal"
            dataSource={versions}
            renderItem={(item) => (
              <List.Item
                actions={[
                  <Button
                    key="rollback"
                    size="small"
                    type="primary"
                    ghost
                    icon={<RollbackOutlined />}
                    onClick={() => handleRollback(item.id)}
                  >
                    回滚到此版本
                  </Button>,
                ]}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      <Tag color="blue">v{item.version_number}</Tag>
                      <span>
                        {dayjs(item.created_at).format('YYYY-MM-DD HH:mm:ss')}
                      </span>
                    </Space>
                  }
                  description={
                    <Space direction="vertical" size={4}>
                      <Text type="secondary">
                        模板名称: {item.snapshot?.name || '未知'}
                      </Text>
                      <Text type="secondary">
                        页数: {item.snapshot?.pages?.length || 0}
                      </Text>
                      <Text type="secondary">
                        元素总数:{' '}
                        {(item.snapshot?.pages || []).reduce(
                          (s, p) => s + (p.elements?.length || 0),
                          0
                        )}
                      </Text>
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Modal>
    </div>
  );
}

export default TemplateDetail;
