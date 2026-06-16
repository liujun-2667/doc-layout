import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import {
  Card,
  Button,
  Select,
  Space,
  Input,
  InputNumber,
  Form,
  Modal,
  message,
  Drawer,
  List,
  Tag,
  Tooltip,
  Popconfirm,
  Empty,
  Slider,
} from 'antd';
import {
  ArrowLeftOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
  RotateLeftOutlined,
  RotateRightOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  EditOutlined,
  DeleteOutlined,
  MergeOutlined,
  SplitCellsOutlined,
  OrderedListOutlined,
  SaveOutlined,
  ReloadOutlined,
  PictureOutlined,
} from '@ant-design/icons';
import { taskApi, pageApi, analysisApi } from '../services/api';
import { ELEMENT_COLORS, ELEMENT_TYPES, getElementColor } from '../constants/elements';

const { Option } = Select;
const { TextArea } = Input;

function Proofread() {
  const { taskId } = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [task, setTask] = useState(null);
  const [pages, setPages] = useState([]);
  const [currentPage, setCurrentPage] = useState(null);
  const [elements, setElements] = useState([]);
  const [selectedElementId, setSelectedElementId] = useState(null);
  const [zoom, setZoom] = useState(100);
  const [showOverlay, setShowOverlay] = useState(true);
  const [viewMode, setViewMode] = useState('processed');
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [editingElement, setEditingElement] = useState(null);
  const [form] = Form.useForm();
  const [rotationAngle, setRotationAngle] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [dragType, setDragType] = useState(null);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const imageRef = useRef(null);
  const containerRef = useRef(null);
  const elementsRef = useRef([]);

  const pageNumParam = searchParams.get('page');

  useEffect(() => {
    elementsRef.current = elements;
  }, [elements]);

  useEffect(() => {
    fetchTask();
  }, [taskId]);

  const fetchTask = async () => {
    try {
      const data = await taskApi.get(taskId);
      setTask(data);
      setPages(data.pages || []);
      if (data.pages && data.pages.length > 0) {
        const pageIndex = pageNumParam
          ? data.pages.findIndex((p) => p.page_number === parseInt(pageNumParam))
          : 0;
        const targetPage = data.pages[pageIndex >= 0 ? pageIndex : 0];
        if (targetPage) {
          selectPage(targetPage);
        }
      }
    } catch (error) {
      message.error('获取任务信息失败');
    }
  };

  const selectPage = async (page) => {
    setCurrentPage(page);
    setSearchParams({ page: page.page_number });
    setRotationAngle(page.rotation_angle || 0);
    setSelectedElementId(null);

    try {
      const pageData = await pageApi.get(page.id);
      const sortedElements = (pageData.elements || []).sort(
        (a, b) => a.reading_order - b.reading_order
      );
      setElements(sortedElements);
    } catch (error) {
      setElements(page.elements || []);
    }
  };

  const selectedElement = elements.find((e) => e.id === selectedElementId);

  const handleElementClick = (elementId, e) => {
    e.stopPropagation();
    setSelectedElementId(elementId);
    setDrawerVisible(true);
    const element = elements.find((e) => e.id === elementId);
    if (element) {
      setEditingElement(element);
      form.setFieldsValue({
        element_type: element.element_type,
        text_content: element.text_content || '',
        x: element.x,
        y: element.y,
        width: element.width,
        height: element.height,
        reading_order: element.reading_order,
        level: element.level || 1,
      });
    }
  };

  const handleSaveElement = async (values) => {
    if (!selectedElementId) return;

    try {
      const updated = await analysisApi.updateElement(selectedElementId, values);
      setElements((prev) =>
        prev.map((e) => (e.id === selectedElementId ? { ...e, ...values } : e))
      );
      setEditingElement({ ...editingElement, ...values });
      message.success('保存成功');
    } catch (error) {
      message.error('保存失败');
    }
  };

  const handleDeleteElement = async () => {
    if (!selectedElementId) return;

    try {
      await analysisApi.deleteElement(selectedElementId);
      setElements((prev) => prev.filter((e) => e.id !== selectedElementId));
      setSelectedElementId(null);
      setDrawerVisible(false);
      message.success('删除成功');
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleRotate = async (delta) => {
    if (!currentPage) return;

    const newAngle = rotationAngle + delta;
    setRotationAngle(newAngle);

    try {
      await pageApi.reprocess(currentPage.id, newAngle);
      message.success('旋转成功');
      const pageData = await pageApi.get(currentPage.id);
      const sortedElements = (pageData.elements || []).sort(
        (a, b) => a.reading_order - b.reading_order
      );
      setElements(sortedElements);
    } catch (error) {
      message.error('旋转失败');
      setRotationAngle(rotationAngle - delta);
    }
  };

  const handleImageMouseDown = (e) => {
    if (!selectedElementId || !containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / (zoom / 100);
    const y = (e.clientY - rect.top) / (zoom / 100);

    const elem = elements.find((e) => e.id === selectedElementId);
    if (!elem) return;

    const elemRight = elem.x + elem.width;
    const elemBottom = elem.y + elem.height;

    const handleSize = 8;

    if (
      Math.abs(x - elemRight) < handleSize &&
      Math.abs(y - elemBottom) < handleSize
    ) {
      setDragType('resize-br');
    } else if (Math.abs(x - elemRight) < handleSize) {
      setDragType('resize-e');
    } else if (Math.abs(y - elemBottom) < handleSize) {
      setDragType('resize-s');
    } else if (
      x >= elem.x &&
      x <= elemRight &&
      y >= elem.y &&
      y <= elemBottom
    ) {
      setDragType('move');
    } else {
      return;
    }

    setIsDragging(true);
    setDragStart({ x, y, elemX: elem.x, elemY: elem.y, elemW: elem.width, elemH: elem.height });
    e.preventDefault();
  };

  const handleImageMouseMove = useCallback(
    (e) => {
      if (!isDragging || !containerRef.current || !selectedElementId) return;

      const rect = containerRef.current.getBoundingClientRect();
      const x = (e.clientX - rect.left) / (zoom / 100);
      const y = (e.clientY - rect.top) / (zoom / 100);

      const dx = x - dragStart.x;
      const dy = y - dragStart.y;

      setElements((prev) =>
        prev.map((elem) => {
          if (elem.id !== selectedElementId) return elem;

          let newX = dragStart.elemX;
          let newY = dragStart.elemY;
          let newW = dragStart.elemW;
          let newH = dragStart.elemH;

          if (dragType === 'move') {
            newX = Math.max(0, dragStart.elemX + dx);
            newY = Math.max(0, dragStart.elemY + dy);
          }
          if (dragType === 'resize-e' || dragType === 'resize-br') {
            newW = Math.max(20, dragStart.elemW + dx);
          }
          if (dragType === 'resize-s' || dragType === 'resize-br') {
            newH = Math.max(20, dragStart.elemH + dy);
          }

          return { ...elem, x: newX, y: newY, width: newW, height: newH };
        })
      );
    },
    [isDragging, dragStart, dragType, zoom, selectedElementId]
  );

  const handleImageMouseUp = useCallback(() => {
    if (isDragging && selectedElementId) {
      const elem = elementsRef.current.find((e) => e.id === selectedElementId);
      if (elem) {
        analysisApi.updateElement(selectedElementId, {
          x: elem.x,
          y: elem.y,
          width: elem.width,
          height: elem.height,
        }).catch(() => {});
      }
    }
    setIsDragging(false);
    setDragType(null);
  }, [isDragging, selectedElementId]);

  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleImageMouseMove);
      document.addEventListener('mouseup', handleImageMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleImageMouseMove);
        document.removeEventListener('mouseup', handleImageMouseUp);
      };
    }
  }, [isDragging, handleImageMouseMove, handleImageMouseUp]);

  const handleZoom = (delta) => {
    setZoom((prev) => Math.max(25, Math.min(400, prev + delta)));
  };

  const getImageUrl = (page) => {
    if (!page) return '';
    if (viewMode === 'original') {
      return page.original_image_path
        ? `/results/${taskId}/page_${String(page.page_number).padStart(4, '0')}/original.png`
        : '';
    }
    return page.processed_image_path
      ? `/results/${taskId}/page_${String(page.page_number).padStart(4, '0')}/processed.png`
      : '';
  };

  const renderElementBox = (elem) => {
    const color = getElementColor(elem.element_type);
    const isSelected = elem.id === selectedElementId;

    return (
      <div
        key={elem.id}
        className={`element-box ${isSelected ? 'selected' : ''}`}
        style={{
          left: `${elem.x}px`,
          top: `${elem.y}px`,
          width: `${elem.width}px`,
          height: `${elem.height}px`,
          borderColor: color.border,
          background: isSelected ? `${color.border}33` : color.bg,
        }}
        onClick={(e) => handleElementClick(elem.id, e)}
      >
        <span className="element-label" style={{ background: color.border }}>
          {color.label}
        </span>
        <span className="order-badge">{elem.reading_order}</span>
        {isSelected && (
          <>
            <div
              style={{
                position: 'absolute',
                right: -4,
                bottom: -4,
                width: 8,
                height: 8,
                background: '#fff',
                border: `2px solid ${color.border}`,
                borderRadius: '50%',
                cursor: 'se-resize',
              }}
            />
          </>
        )}
      </div>
    );
  };

  const sortedByOrder = [...elements].sort((a, b) => a.reading_order - b.reading_order);

  return (
    <div style={{ height: 'calc(100vh - 64px - 48px)', display: 'flex', flexDirection: 'column' }}>
      <Card
        size="small"
        style={{ marginBottom: 12, flexShrink: 0 }}
        bodyStyle={{ padding: '8px 16px' }}
      >
        <Space>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate(`/tasks/${taskId}`)}
          >
            返回
          </Button>

          <span style={{ fontWeight: 'bold' }}>
            {task?.filename || ''}
          </span>

          <Space.Split />

          <Tooltip title="放大">
            <Button
              size="small"
              icon={<ZoomInOutlined />}
              onClick={() => handleZoom(25)}
            />
          </Tooltip>
          <span style={{ minWidth: 50, textAlign: 'center' }}>{zoom}%</span>
          <Tooltip title="缩小">
            <Button
              size="small"
              icon={<ZoomOutOutlined />}
              onClick={() => handleZoom(-25)}
            />
          </Tooltip>

          <Space.Split />

          <Select
            size="small"
            value={viewMode}
            onChange={setViewMode}
            style={{ width: 120 }}
          >
            <Option value="processed">处理后图像</Option>
            <Option value="original">原始图像</Option>
          </Select>

          <Tooltip title="逆时针旋转">
            <Button
              size="small"
              icon={<RotateLeftOutlined />}
              onClick={() => handleRotate(-5)}
            />
          </Tooltip>
          <Tooltip title="顺时针旋转">
            <Button
              size="small"
              icon={<RotateRightOutlined />}
              onClick={() => handleRotate(5)}
            />
          </Tooltip>
          <span style={{ fontSize: 12, color: '#666' }}>
            旋转: {rotationAngle.toFixed(1)}°
          </span>

          <Space.Split />

          <Button
            size="small"
            icon={showOverlay ? <EyeOutlined /> : <EyeInvisibleOutlined />}
            onClick={() => setShowOverlay(!showOverlay)}
          >
            {showOverlay ? '隐藏标注' : '显示标注'}
          </Button>

          <Space style={{ marginLeft: 'auto' }}>
            <span style={{ fontSize: 12, color: '#666' }}>
              共 {elements.length} 个元素
            </span>
          </Space>
        </Space>
      </Card>

      <div style={{ flex: 1, display: 'flex', gap: 12, minHeight: 0 }}>
        <div
          style={{
            width: 120,
            background: '#fff',
            borderRadius: 8,
            padding: 8,
            overflowY: 'auto',
            flexShrink: 0,
          }}
        >
          <div style={{ fontWeight: 'bold', marginBottom: 8, fontSize: 13 }}>
            页面列表
          </div>
          {pages.map((page) => (
            <div
              key={page.id}
              className={`page-list-item ${currentPage?.id === page.id ? 'active' : ''}`}
              onClick={() => selectPage(page)}
              style={{
                marginBottom: 8,
                cursor: 'pointer',
                padding: 4,
                borderRadius: 4,
                border:
                  currentPage?.id === page.id
                    ? '2px solid #1890ff'
                    : '1px solid #d9d9d9',
                background: currentPage?.id === page.id ? '#e6f7ff' : '#fff',
              }}
            >
              <div
                style={{
                  height: 80,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: '#f5f5f5',
                  marginBottom: 4,
                }}
              >
                <PictureOutlined style={{ fontSize: 24, color: '#ccc' }} />
              </div>
              <div style={{ fontSize: 12, textAlign: 'center' }}>
                第 {page.page_number} 页
              </div>
              <div style={{ fontSize: 10, color: '#999', textAlign: 'center' }}>
                {page.elements?.length || 0} 元素
              </div>
            </div>
          ))}
        </div>

        <div
          className="image-panel"
          ref={containerRef}
          onMouseDown={handleImageMouseDown}
          style={{
            flex: 1,
            background: '#fff',
            borderRadius: 8,
            overflow: 'auto',
            position: 'relative',
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'center',
            padding: 20,
          }}
        >
          {currentPage ? (
            <div
              className="image-container"
              style={{
                transform: `scale(${zoom / 100})`,
                transformOrigin: 'top left',
                position: 'relative',
              }}
            >
              <img
                ref={imageRef}
                src={getImageUrl(currentPage)}
                alt={`第 ${currentPage.page_number} 页`}
                style={{
                  maxWidth: 'none',
                  display: 'block',
                }}
                draggable={false}
              />
              {showOverlay && (
                <div className="layout-overlay">
                  {elements.map(renderElementBox)}
                </div>
              )}
            </div>
          ) : (
            <Empty description="请选择页面" />
          )}
        </div>

        <div
          className="elements-panel"
          style={{
            width: 320,
            background: '#fff',
            borderRadius: 8,
            padding: 16,
            overflowY: 'auto',
            flexShrink: 0,
          }}
        >
          <div style={{ fontWeight: 'bold', marginBottom: 12, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span>元素列表</span>
            <Tag color="blue">{elements.length}</Tag>
          </div>

          <List
            size="small"
            dataSource={sortedByOrder}
            renderItem={(elem) => {
              const color = getElementColor(elem.element_type);
              const isSelected = elem.id === selectedElementId;

              return (
                <List.Item
                  className={`element-item ${isSelected ? 'selected' : ''}`}
                  style={{
                    cursor: 'pointer',
                    padding: '6px 8px',
                    borderRadius: 4,
                    marginBottom: 4,
                    background: isSelected ? '#e6f7ff' : 'transparent',
                  }}
                  onClick={() => {
                    setSelectedElementId(elem.id);
                    setDrawerVisible(true);
                    const element = elements.find((e) => e.id === elem.id);
                    if (element) {
                      setEditingElement(element);
                      form.setFieldsValue({
                        element_type: element.element_type,
                        text_content: element.text_content || '',
                        x: element.x,
                        y: element.y,
                        width: element.width,
                        height: element.height,
                        reading_order: element.reading_order,
                        level: element.level || 1,
                      });
                    }
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, width: '100%' }}>
                    <span
                      className="element-type-tag"
                      style={{ background: color.border }}
                    >
                      {color.label}
                    </span>
                    <div className="element-info" style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: 500 }}>
                        #{elem.reading_order} {elem.element_type}
                      </div>
                      <div className="element-text-preview">
                        {(elem.text_content || '').slice(0, 30) || '无文本'}
                      </div>
                    </div>
                    <div style={{ fontSize: 11, color: '#999' }}>
                      {Math.round(elem.width)}×{Math.round(elem.height)}
                    </div>
                  </div>
                </List.Item>
              );
            }}
          />
        </div>
      </div>

      <Drawer
        title="编辑元素"
        placement="right"
        width={400}
        open={drawerVisible}
        onClose={() => setDrawerVisible(false)}
        extra={
          <Space>
            <Popconfirm
              title="确定删除此元素？"
              onConfirm={handleDeleteElement}
            >
              <Button danger icon={<DeleteOutlined />}>
                删除
              </Button>
            </Popconfirm>
            <Button type="primary" icon={<SaveOutlined />} onClick={form.submit}>
              保存
            </Button>
          </Space>
        }
      >
        {editingElement && (
          <Form
            form={form}
            layout="vertical"
            onFinish={handleSaveElement}
          >
            <Form.Item label="元素类型" name="element_type">
              <Select>
                {ELEMENT_TYPES.map((type) => (
                  <Option key={type.value} value={type.value}>
                    {type.label}
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item label="阅读顺序" name="reading_order">
              <InputNumber min={1} style={{ width: '100%' }} />
            </Form.Item>

            <Form.Item label="标题级别" name="level">
              <Select>
                <Option value={1}>一级标题</Option>
                <Option value={2}>二级标题</Option>
                <Option value={3}>三级标题</Option>
              </Select>
            </Form.Item>

            <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
              <Form.Item label="X" name="x" style={{ flex: 1 }}>
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item label="Y" name="y" style={{ flex: 1 }}>
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
            </div>
            <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
              <Form.Item label="宽度" name="width" style={{ flex: 1 }}>
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item label="高度" name="height" style={{ flex: 1 }}>
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
            </div>

            <Form.Item label="文本内容" name="text_content">
              <TextArea rows={6} placeholder="元素的文本内容" />
            </Form.Item>

            <div style={{ padding: 12, background: '#f5f5f5', borderRadius: 4 }}>
              <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>
                元素 ID: {editingElement.id}
              </div>
              <div style={{ fontSize: 12, color: '#666' }}>
                置信度: {(editingElement.confidence * 100).toFixed(1)}%
              </div>
            </div>
          </Form>
        )}
      </Drawer>
    </div>
  );
}

export default Proofread;
