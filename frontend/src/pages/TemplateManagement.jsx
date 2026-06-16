import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Row,
  Col,
  Tag,
  Input,
  Select,
  Button,
  Space,
  Typography,
  Empty,
  Tooltip,
  Popconfirm,
  message,
} from 'antd';
import {
  SearchOutlined,
  DeleteOutlined,
  EyeOutlined,
  EditOutlined,
  FireOutlined,
  ClockCircleOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { templateApi } from '../services/api';
import { ELEMENT_COLORS, getElementColor } from '../constants/elements';

const { Title, Text } = Typography;
const { Option } = Select;

const DOCUMENT_TYPES = [
  { value: '论文', label: '论文', color: 'blue' },
  { value: '报告', label: '报告', color: 'purple' },
  { value: '发票', label: '发票', color: 'green' },
  { value: '合同', label: '合同', color: 'orange' },
  { value: '简历', label: '简历', color: 'cyan' },
];

function TemplateThumbnail({ template }) {
  const viewBoxWidth = 200;
  const viewBoxHeight = 282;
  const firstPage = template.pages?.[0];

  if (!firstPage || !firstPage.elements || firstPage.elements.length === 0) {
    return (
      <div
        style={{
          width: '100%',
          height: 120,
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
        height: 120,
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
      {firstPage.elements.map((elem) => {
        const color = getElementColor(elem.element_type);
        const x = elem.rel_x * viewBoxWidth;
        const y = elem.rel_y * viewBoxHeight;
        const w = elem.rel_width * viewBoxWidth;
        const h = elem.rel_height * viewBoxHeight;
        return (
          <rect
            key={elem.id}
            x={x}
            y={y}
            width={Math.max(w, 2)}
            height={Math.max(h, 2)}
            fill={color.bg}
            stroke={color.border}
            strokeWidth="0.8"
            rx="1"
          />
        );
      })}
    </svg>
  );
}

function TemplateManagement() {
  const navigate = useNavigate();
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [filterType, setFilterType] = useState(null);
  const [sortBy, setSortBy] = useState('created_at');
  const [total, setTotal] = useState(0);

  const fetchTemplates = async () => {
    setLoading(true);
    try {
      const params = {
        skip: 0,
        limit: 100,
        sort_by: sortBy,
      };
      if (filterType) params.document_type = filterType;
      if (searchText) params.search = searchText;

      const data = await templateApi.list(params);
      setTemplates(data.templates || []);
      setTotal(data.total || 0);
    } catch (error) {
      message.error('加载模板列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTemplates();
  }, [sortBy, filterType, searchText]);

  const handleDelete = async (templateId, templateName) => {
    try {
      await templateApi.delete(templateId);
      message.success(`已删除模板: ${templateName}`);
      fetchTemplates();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleSearch = (e) => {
    setSearchText(e.target.value);
  };

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
        <Title level={3} style={{ margin: 0 }}>
          版面模板管理
        </Title>
      </div>

      <Card style={{ marginBottom: 16 }}>
        <Space wrap size="middle">
          <Input
            prefix={<SearchOutlined />}
            placeholder="搜索模板名称"
            value={searchText}
            onChange={handleSearch}
            style={{ width: 240 }}
            allowClear
          />
          <Select
            placeholder="按文档类型筛选"
            value={filterType}
            onChange={setFilterType}
            style={{ width: 180 }}
            allowClear
          >
            {DOCUMENT_TYPES.map((t) => (
              <Option key={t.value} value={t.value}>
                {t.label}
              </Option>
            ))}
          </Select>
          <Select
            placeholder="排序方式"
            value={sortBy}
            onChange={setSortBy}
            style={{ width: 180 }}
          >
            <Option value="created_at">
              <Space>
                <ClockCircleOutlined />
                按创建时间
              </Space>
            </Option>
            <Option value="match_count">
              <Space>
                <FireOutlined />
                按匹配次数
              </Space>
            </Option>
          </Select>
          <Text type="secondary" style={{ marginLeft: 16 }}>
            共 {total} 个模板
          </Text>
        </Space>
      </Card>

      {templates.length === 0 && !loading ? (
        <Empty description="暂无模板,请在校对页面保存版面为模板" />
      ) : (
        <Row gutter={[16, 16]}>
          {templates.map((template) => (
            <Col xs={24} sm={12} md={8} lg={6} key={template.id}>
              <Card
                hoverable
                loading={loading}
                onClick={() => navigate(`/templates/${template.id}`)}
                style={{ height: '100%' }}
                bodyStyle={{ padding: 0 }}
                cover={
                  <div style={{ padding: 8 }}>
                    <TemplateThumbnail template={template} />
                  </div>
                }
                actions={[
                  <Tooltip key="view" title="查看详情">
                    <EyeOutlined
                      key="view"
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/templates/${template.id}`);
                      }}
                    />
                  </Tooltip>,
                  <Tooltip key="edit" title="编辑">
                    <EditOutlined
                      key="edit"
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/templates/${template.id}`);
                      }}
                    />
                  </Tooltip>,
                  <Popconfirm
                    key="delete"
                    title={`确定删除模板「${template.name}」吗?`}
                    onConfirm={(e) => {
                      e?.stopPropagation();
                      handleDelete(template.id, template.name);
                    }}
                    onCancel={(e) => e?.stopPropagation()}
                    okText="删除"
                    cancelText="取消"
                  >
                    <DeleteOutlined
                      key="delete"
                      onClick={(e) => e.stopPropagation()}
                      style={{ color: '#ff4d4f' }}
                    />
                  </Popconfirm>,
                ]}
              >
                <div style={{ padding: '8px 16px 16px' }}>
                  <div
                    style={{
                      fontWeight: 'bold',
                      fontSize: 14,
                      marginBottom: 8,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {template.name}
                  </div>
                  <div style={{ marginBottom: 8 }}>
                    {(template.document_types || []).map((type) => {
                      const typeInfo = DOCUMENT_TYPES.find((t) => t.value === type);
                      return (
                        <Tag
                          key={type}
                          color={typeInfo?.color || 'default'}
                          style={{ marginBottom: 4 }}
                        >
                          {type}
                        </Tag>
                      );
                    })}
                  </div>
                  <Space split size={8} style={{ fontSize: 12, color: '#999' }}>
                    <span>
                      <FireOutlined style={{ marginRight: 4 }} />
                      匹配 {template.match_count || 0} 次
                    </span>
                    <span>
                      <ClockCircleOutlined style={{ marginRight: 4 }} />
                      {dayjs(template.created_at).format('YYYY-MM-DD')}
                    </span>
                  </Space>
                  {template.description && (
                    <div
                      style={{
                        marginTop: 8,
                        fontSize: 12,
                        color: '#666',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {template.description}
                    </div>
                  )}
                </div>
              </Card>
            </Col>
          ))}
        </Row>
      )}
    </div>
  );
}

export default TemplateManagement;
