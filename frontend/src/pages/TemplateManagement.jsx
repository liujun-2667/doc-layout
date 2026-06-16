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
  Form,
  Checkbox,
  Divider,
  InputNumber,
  Modal,
} from 'antd';
import {
  SearchOutlined,
  DeleteOutlined,
  EyeOutlined,
  EditOutlined,
  FireOutlined,
  ClockCircleOutlined,
  FileTextOutlined,
  SwapOutlined,
  PlusOutlined,
  MinusOutlined,
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

function CompositeTemplateThumbnail({ template }) {
  const rules = template.rules || [];

  return (
    <div
      style={{
        width: '100%',
        height: 120,
        background: 'linear-gradient(135deg, #f9f0ff 0%, #e6f7ff 100%)',
        borderRadius: 4,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        border: '2px dashed #722ed1',
      }}
    >
      <SwapOutlined style={{ fontSize: 32, color: '#722ed1', marginBottom: 8 }} />
      <div style={{ fontSize: 12, color: '#722ed1', fontWeight: 500 }}>
        组合模板
      </div>
      <div style={{ fontSize: 11, color: '#9254de', marginTop: 4 }}>
        {rules.length} 条规则
      </div>
    </div>
  );
}

function TemplateManagement() {
  const navigate = useNavigate();
  const [templates, setTemplates] = useState([]);
  const [compositeTemplates, setCompositeTemplates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [filterType, setFilterType] = useState(null);
  const [sortBy, setSortBy] = useState('created_at');
  const [total, setTotal] = useState(0);
  const [createCompositeModalVisible, setCreateCompositeModalVisible] = useState(false);
  const [compositeForm] = Form.useForm();
  const [compositeRules, setCompositeRules] = useState([
    { base_template_id: '', start_page: 1, end_page: null, end_page_is_last: true },
  ]);
  const [availableTemplates, setAvailableTemplates] = useState([]);

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
      setCompositeTemplates(data.composite_templates || []);
      setAvailableTemplates(data.templates || []);
      setTotal(data.total || 0);
    } catch (error) {
      message.error('加载模板列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleAddRule = () => {
    setCompositeRules([
      ...compositeRules,
      { base_template_id: '', start_page: 1, end_page: null, end_page_is_last: false },
    ]);
  };

  const handleRemoveRule = (index) => {
    if (compositeRules.length <= 1) {
      message.warning('至少需要一条规则');
      return;
    }
    setCompositeRules(compositeRules.filter((_, i) => i !== index));
  };

  const handleRuleChange = (index, field, value) => {
    const newRules = [...compositeRules];
    newRules[index] = { ...newRules[index], [field]: value };
    if (field === 'end_page_is_last' && value) {
      newRules[index].end_page = null;
    }
    setCompositeRules(newRules);
  };

  const handleCreateComposite = async (values) => {
    try {
      const validRules = compositeRules.filter(
        (r) => r.base_template_id && r.start_page > 0
      );
      if (validRules.length === 0) {
        message.error('请至少填写一条有效的规则');
        return;
      }

      const result = await templateApi.createComposite({
        name: values.name,
        document_types: values.document_types,
        description: values.description,
        rules: validRules.map((r) => ({
          base_template_id: r.base_template_id,
          start_page: r.start_page,
          end_page: r.end_page_is_last ? null : r.end_page,
          end_page_is_last: r.end_page_is_last,
        })),
      });

      message.success(`组合模板「${result.name}」创建成功`);
      setCreateCompositeModalVisible(false);
      compositeForm.resetFields();
      setCompositeRules([
        { base_template_id: '', start_page: 1, end_page: null, end_page_is_last: true },
      ]);
      fetchTemplates();
    } catch (error) {
      if (error.response?.status === 409) {
        message.error('已存在同名模板');
      } else {
        message.error('创建组合模板失败');
      }
    }
  };

  const handleDeleteComposite = async (templateId, templateName) => {
    try {
      await templateApi.deleteComposite(templateId);
      message.success(`已删除组合模板: ${templateName}`);
      fetchTemplates();
    } catch (error) {
      message.error('删除失败');
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
        <Space>
          <Button
            type="primary"
            icon={<SwapOutlined />}
            onClick={() => {
              setCreateCompositeModalVisible(true);
              compositeForm.resetFields();
              setCompositeRules([
                { base_template_id: '', start_page: 1, end_page: null, end_page_is_last: true },
              ]);
            }}
          >
            创建组合模板
          </Button>
        </Space>
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

      {templates.length === 0 && compositeTemplates.length === 0 && !loading ? (
        <Empty description="暂无模板,请在校对页面保存版面为模板" />
      ) : (
        <>
          {compositeTemplates.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <Title level={5} style={{ margin: '0 0 12px 0', color: '#722ed1' }}>
                <Space>
                  <SwapOutlined />
                  组合模板 ({compositeTemplates.length})
                </Space>
              </Title>
              <Row gutter={[16, 16]}>
                {compositeTemplates.map((template) => (
                  <Col xs={24} sm={12} md={8} lg={6} key={template.id}>
                    <Card
                      hoverable
                      loading={loading}
                      onClick={() => navigate(`/templates/${template.id}`)}
                      style={{
                        height: '100%',
                        border: '2px solid #722ed1',
                        boxShadow: '0 2px 8px rgba(114, 46, 209, 0.15)',
                      }}
                      bodyStyle={{ padding: 0 }}
                      cover={
                        <div style={{ padding: 8 }}>
                          <CompositeTemplateThumbnail template={template} />
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
                          title={`确定删除组合模板「${template.name}」吗?`}
                          onConfirm={(e) => {
                            e?.stopPropagation();
                            handleDeleteComposite(template.id, template.name);
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
                            display: 'flex',
                            alignItems: 'center',
                            gap: 4,
                          }}
                        >
                          <Tag color="purple" icon={<SwapOutlined />} style={{ margin: 0 }}>
                            组合
                          </Tag>
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
                        <div style={{ marginTop: 8, fontSize: 11, color: '#9254de' }}>
                          {template.rules?.length || 0} 条规则 · 引用 {new Set(template.rules?.map(r => r.base_template_id)).size || 0} 个基础模板
                        </div>
                        {template.description && (
                          <div
                            style={{
                              marginTop: 4,
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
            </div>
          )}

          {templates.length > 0 && (
            <div>
              <Title level={5} style={{ margin: '0 0 12px 0', color: '#1890ff' }}>
                <Space>
                  <FileTextOutlined />
                  基础模板 ({templates.length})
                </Space>
              </Title>
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
            </div>
          )}
        </>
      )}

      <Modal
        title={
          <Space>
            <SwapOutlined />
            创建组合模板
          </Space>
        }
        open={createCompositeModalVisible}
        onCancel={() => setCreateCompositeModalVisible(false)}
        width={640}
        footer={null}
      >
        <Form
          form={compositeForm}
          layout="vertical"
          onFinish={handleCreateComposite}
        >
          <Form.Item
            label="组合模板名称"
            name="name"
            rules={[{ required: true, message: '请输入模板名称' }]}
          >
            <Input placeholder="请输入组合模板名称,如:期刊论文完整模板" />
          </Form.Item>
          <Form.Item
            label="适用文档类型(可多选)"
            name="document_types"
            rules={[{ required: true, message: '请选择至少一种文档类型' }]}
          >
            <Select mode="multiple" placeholder="选择该模板适用的文档类型">
              {DOCUMENT_TYPES.map((t) => (
                <Option key={t.value} value={t.value}>
                  {t.label}
                </Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item label="备注说明" name="description">
            <TextArea
              rows={2}
              placeholder="可选:添加模板的描述信息,如适用场景、特殊说明等"
            />
          </Form.Item>

          <Divider orientation="left">
            <Space>
              <span>组合规则</span>
              <Text type="secondary" style={{ fontSize: 12 }}>
                按页码范围指定各页面使用的基础模板
              </Text>
            </Space>
          </Divider>

          <div style={{ marginBottom: 16 }}>
            {compositeRules.map((rule, index) => (
              <Card
                key={index}
                size="small"
                style={{ marginBottom: 8 }}
                title={
                  <Space>
                    <Tag color="purple">规则 {index + 1}</Tag>
                  </Space>
                }
                extra={
                  <Button
                    type="text"
                    danger
                    size="small"
                    icon={<MinusOutlined />}
                    onClick={() => handleRemoveRule(index)}
                  >
                    移除
                  </Button>
                }
              >
                <Row gutter={8}>
                  <Col span={10}>
                    <Form.Item label="基础模板" style={{ marginBottom: 8 }}>
                      <Select
                        value={rule.base_template_id}
                        onChange={(value) => handleRuleChange(index, 'base_template_id', value)}
                        placeholder="选择基础模板"
                        showSearch
                        optionFilterProp="children"
                      >
                        {availableTemplates.map((t) => (
                          <Option key={t.id} value={t.id}>
                            {t.name}
                          </Option>
                        ))}
                      </Select>
                    </Form.Item>
                  </Col>
                  <Col span={5}>
                    <Form.Item label="起始页" style={{ marginBottom: 8 }}>
                      <InputNumber
                        min={1}
                        value={rule.start_page}
                        onChange={(value) => handleRuleChange(index, 'start_page', value)}
                        style={{ width: '100%' }}
                      />
                    </Form.Item>
                  </Col>
                  <Col span={5}>
                    <Form.Item label="结束页" style={{ marginBottom: 8 }}>
                      {rule.end_page_is_last ? (
                        <Tag color="blue" style={{ width: '100%', textAlign: 'center' }}>
                          末页
                        </Tag>
                      ) : (
                        <InputNumber
                          min={rule.start_page}
                          value={rule.end_page}
                          onChange={(value) => handleRuleChange(index, 'end_page', value)}
                          style={{ width: '100%' }}
                          placeholder="页码"
                        />
                      )}
                    </Form.Item>
                  </Col>
                  <Col span={4}>
                    <Form.Item label="&nbsp;" style={{ marginBottom: 8 }}>
                      <Checkbox
                        checked={rule.end_page_is_last}
                        onChange={(e) => handleRuleChange(index, 'end_page_is_last', e.target.checked)}
                      >
                        末页
                      </Checkbox>
                    </Form.Item>
                  </Col>
                </Row>
              </Card>
            ))}
            <Button
              type="dashed"
              icon={<PlusOutlined />}
              onClick={handleAddRule}
              style={{ width: '100%' }}
            >
              添加规则
            </Button>
          </div>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                创建组合模板
              </Button>
              <Button onClick={() => setCreateCompositeModalVisible(false)}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

export default TemplateManagement;
