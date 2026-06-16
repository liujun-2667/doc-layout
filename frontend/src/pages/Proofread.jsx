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
  Checkbox,
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
  ColumnWidthOutlined,
  HolderOutlined,
  CloseOutlined,
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
  const [selectedElementIds, setSelectedElementIds] = useState([]);
  const [zoom, setZoom] = useState(100);
  const [showOverlay, setShowOverlay] = useState(true);
  const [viewMode, setViewMode] = useState('processed');
  const [compareMode, setCompareMode] = useState(false);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [editingElement, setEditingElement] = useState(null);
  const [form] = Form.useForm();
  const [rotationAngle, setRotationAngle] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [dragType, setDragType] = useState(null);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [splitMode, setSplitMode] = useState(false);
  const [splitLineStart, setSplitLineStart] = useState(null);
  const [splitLineEnd, setSplitLineEnd] = useState(null);
  const [isDrawingSplitLine, setIsDrawingSplitLine] = useState(false);
  const [dragItemId, setDragItemId] = useState(null);
  const [dragOverItemId, setDragOverItemId] = useState(null);
  const imageRef = useRef(null);
  const imageRefOriginal = useRef(null);
  const imageRefProcessed = useRef(null);
  const containerRef = useRef(null);
  const leftPanelRef = useRef(null);
  const rightPanelRef = useRef(null);
  const elementsRef = useRef([]);
  const isSyncingScroll = useRef(false);

  const getActiveContainerRef = () => {
    return compareMode ? rightPanelRef : containerRef;
  };

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
    setSelectedElementIds([]);
    setSplitMode(false);

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

    if (splitMode) {
      if (elementId !== selectedElementId) {
        message.info('拆分模式下只能拆分已选中的区域，请先退出拆分模式');
        return;
      }
      return;
    }

    if (e.ctrlKey || e.metaKey) {
      setSelectedElementIds((prev) => {
        if (prev.includes(elementId)) {
          return prev.filter((id) => id !== elementId);
        }
        return [...prev, elementId];
      });
    } else {
      setSelectedElementIds([elementId]);
    }
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

  const handleBackgroundClick = () => {
    if (!splitMode) {
      setSelectedElementId(null);
      setSelectedElementIds([]);
      setDrawerVisible(false);
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
      setSelectedElementIds([]);
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
    const activeContainer = getActiveContainerRef().current;
    if (!activeContainer) return;

    const rect = activeContainer.getBoundingClientRect();
    const x = (e.clientX - rect.left) / (zoom / 100);
    const y = (e.clientY - rect.top) / (zoom / 100);

    if (splitMode && selectedElementId) {
      const elem = elements.find((el) => el.id === selectedElementId);
      if (!elem) return;

      if (
        x >= elem.x &&
        x <= elem.x + elem.width &&
        y >= elem.y &&
        y <= elem.y + elem.height
      ) {
        setIsDrawingSplitLine(true);
        setSplitLineStart({ x, y });
        setSplitLineEnd({ x, y });
        e.preventDefault();
        return;
      }
    }

    if (!selectedElementId) return;

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
      const activeContainer = getActiveContainerRef().current;
      if (!activeContainer) return;

      const rect = activeContainer.getBoundingClientRect();
      const x = (e.clientX - rect.left) / (zoom / 100);
      const y = (e.clientY - rect.top) / (zoom / 100);

      if (isDrawingSplitLine && splitLineStart) {
        setSplitLineEnd({ x, y });
        return;
      }

      if (!isDragging || !selectedElementId) return;

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
    [isDragging, isDrawingSplitLine, dragStart, dragType, zoom, selectedElementId, splitLineStart, compareMode]
  );

  const handleImageMouseUp = useCallback(() => {
    if (isDrawingSplitLine && splitLineStart && splitLineEnd && selectedElementId) {
      const elem = elementsRef.current.find((e) => e.id === selectedElementId);
      if (elem) {
        const dx = splitLineEnd.x - splitLineStart.x;
        const dy = splitLineEnd.y - splitLineStart.y;

        if (Math.abs(dx) < 10 && Math.abs(dy) < 10) {
          setIsDrawingSplitLine(false);
          setSplitLineStart(null);
          setSplitLineEnd(null);
          return;
        }

        const isHorizontal = Math.abs(dy) > Math.abs(dx);
        let splitPosition;

        if (isHorizontal) {
          const avgY = (splitLineStart.y + splitLineEnd.y) / 2;
          splitPosition = (avgY - elem.y) / elem.height;
        } else {
          const avgX = (splitLineStart.x + splitLineEnd.x) / 2;
          splitPosition = (avgX - elem.x) / elem.width;
        }

        splitPosition = Math.max(0.1, Math.min(0.9, splitPosition));
        const splitType = isHorizontal ? 'horizontal' : 'vertical';

        Modal.confirm({
          title: '确认拆分',
          content: `确定要${isHorizontal ? '水平' : '垂直'}拆分此区域吗？拆分位置约 ${(splitPosition * 100).toFixed(0)}%`,
          onOk: async () => {
            try {
              const result = await analysisApi.splitElement(
                selectedElementId,
                splitType,
                splitPosition
              );
              const sorted = result.sort((a, b) => a.reading_order - b.reading_order);
              setElements(sorted);
              setSelectedElementId(null);
              setSelectedElementIds([]);
              setSplitMode(false);
              message.success('拆分成功');
            } catch (error) {
              message.error('拆分失败');
            }
          },
        });
      }
      setIsDrawingSplitLine(false);
      setSplitLineStart(null);
      setSplitLineEnd(null);
      return;
    }

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
  }, [isDragging, isDrawingSplitLine, selectedElementId, splitLineStart, splitLineEnd, compareMode]);

  useEffect(() => {
    if (isDragging || isDrawingSplitLine) {
      document.addEventListener('mousemove', handleImageMouseMove);
      document.addEventListener('mouseup', handleImageMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleImageMouseMove);
        document.removeEventListener('mouseup', handleImageMouseUp);
      };
    }
  }, [isDragging, isDrawingSplitLine, handleImageMouseMove, handleImageMouseUp, compareMode]);

  const handleZoom = (delta) => {
    setZoom((prev) => Math.max(25, Math.min(400, prev + delta)));
  };

  const getImageUrl = (page, mode = viewMode) => {
    if (!page) return '';
    if (mode === 'original') {
      return page.original_image_path
        ? `/results/${taskId}/page_${String(page.page_number).padStart(4, '0')}/original.png`
        : '';
    }
    return page.processed_image_path
      ? `/results/${taskId}/page_${String(page.page_number).padStart(4, '0')}/processed.png`
      : '';
  };

  const handleMerge = async () => {
    if (selectedElementIds.length < 2) {
      message.warning('请至少选择2个区域进行合并（按住Ctrl点击选择多个）');
      return;
    }

    Modal.confirm({
      title: '确认合并',
      content: `确定要合并选中的 ${selectedElementIds.length} 个区域吗？`,
      onOk: async () => {
        try {
          const result = await analysisApi.mergeElements(currentPage.id, selectedElementIds);
          const sorted = result.sort((a, b) => a.reading_order - b.reading_order);
          setElements(sorted);
          setSelectedElementIds([]);
          setSelectedElementId(null);
          message.success('合并成功');
        } catch (error) {
          message.error('合并失败');
        }
      },
    });
  };

  const handleToggleSplitMode = () => {
    if (!selectedElementId) {
      message.warning('请先选择一个要拆分的区域');
      return;
    }
    setSplitMode(!splitMode);
    setIsDrawingSplitLine(false);
    setSplitLineStart(null);
    setSplitLineEnd(null);
    if (!splitMode) {
      message.info('拆分模式已开启：在选中区域内拖动鼠标绘制分割线');
    }
  };

  const handleComparePanelScroll = (e, sourceRef) => {
    if (isSyncingScroll.current) return;

    const target = e.target;
    const source = sourceRef.current;
    if (!source || !target) return;

    const otherRef = sourceRef === leftPanelRef ? rightPanelRef : leftPanelRef;
    const other = otherRef.current;
    if (!other) return;

    isSyncingScroll.current = true;

    try {
      const scrollRatio = target.scrollTop / (target.scrollHeight - target.clientHeight || 1);
      const maxScroll = other.scrollHeight - other.clientHeight;
      other.scrollTop = scrollRatio * maxScroll;

      const scrollRatioX = target.scrollLeft / (target.scrollWidth - target.clientWidth || 1);
      const maxScrollX = other.scrollWidth - other.clientWidth;
      other.scrollLeft = scrollRatioX * maxScrollX;
    } finally {
      requestAnimationFrame(() => {
        isSyncingScroll.current = false;
      });
    }
  };

  const handleDragStart = (e, elementId) => {
    setDragItemId(elementId);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e, elementId) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (dragOverItemId !== elementId) {
      setDragOverItemId(elementId);
    }
  };

  const handleDragLeave = () => {
    setDragOverItemId(null);
  };

  const handleDrop = async (e, targetElementId) => {
    e.preventDefault();
    if (!dragItemId || dragItemId === targetElementId) {
      setDragItemId(null);
      setDragOverItemId(null);
      return;
    }

    const sortedByOrder = [...elements].sort((a, b) => a.reading_order - b.reading_order);
    const dragIndex = sortedByOrder.findIndex((e) => e.id === dragItemId);
    const targetIndex = sortedByOrder.findIndex((e) => e.id === targetElementId);

    if (dragIndex === -1 || targetIndex === -1) {
      setDragItemId(null);
      setDragOverItemId(null);
      return;
    }

    const newOrder = [...sortedByOrder];
    const [removed] = newOrder.splice(dragIndex, 1);
    newOrder.splice(targetIndex, 0, removed);

    const elementIdOrder = newOrder.map((e) => e.id);

    const localUpdated = newOrder.map((elem, idx) => ({
      ...elem,
      reading_order: idx + 1,
    }));
    setElements(localUpdated.sort((a, b) => a.reading_order - b.reading_order));

    try {
      const result = await analysisApi.reorderElements(currentPage.id, elementIdOrder);
      const sorted = result.sort((a, b) => a.reading_order - b.reading_order);
      setElements(sorted);
      message.success('排序已保存');
    } catch (error) {
      message.error('保存排序失败');
      fetchTask();
    }

    setDragItemId(null);
    setDragOverItemId(null);
  };

  const handleDragEnd = () => {
    setDragItemId(null);
    setDragOverItemId(null);
  };

  const renderSplitLine = () => {
    if (!splitLineStart || !splitLineEnd) return null;

    const dx = splitLineEnd.x - splitLineStart.x;
    const dy = splitLineEnd.y - splitLineStart.y;
    const isHorizontal = Math.abs(dy) > Math.abs(dx);

    const elem = elements.find((e) => e.id === selectedElementId);
    if (!elem) return null;

    let lineStyle;
    if (isHorizontal) {
      const avgY = (splitLineStart.y + splitLineEnd.y) / 2;
      lineStyle = {
        position: 'absolute',
        left: `${elem.x}px`,
        top: `${avgY}px`,
        width: `${elem.width}px`,
        height: '2px',
        background: '#ff4d4f',
        boxShadow: '0 0 4px rgba(255,77,79,0.6)',
        zIndex: 1000,
      };
    } else {
      const avgX = (splitLineStart.x + splitLineEnd.x) / 2;
      lineStyle = {
        position: 'absolute',
        left: `${avgX}px`,
        top: `${elem.y}px`,
        width: '2px',
        height: `${elem.height}px`,
        background: '#ff4d4f',
        boxShadow: '0 0 4px rgba(255,77,79,0.6)',
        zIndex: 1000,
      };
    }

    return <div style={lineStyle} />;
  };

  const renderElementBox = (elem) => {
    const color = getElementColor(elem.element_type);
    const isSelected = elem.id === selectedElementId;
    const isMultiSelected = selectedElementIds.includes(elem.id);

    return (
      <div
        key={elem.id}
        className={`element-box ${isSelected ? 'selected' : ''} ${isMultiSelected && !isSelected ? 'multi-selected' : ''}`}
        style={{
          left: `${elem.x}px`,
          top: `${elem.y}px`,
          width: `${elem.width}px`,
          height: `${elem.height}px`,
          borderColor: color.border,
          background: isSelected ? `${color.border}44` : isMultiSelected ? `${color.border}33` : color.bg,
          outline: isMultiSelected && !isSelected ? `2px dashed ${color.border}` : 'none',
          outlineOffset: '2px',
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

  const renderImagePanel = (mode, panelRef) => {
    const showOverlayHere = mode === 'processed' && showOverlay;

    return (
      <div
        ref={panelRef}
        className="image-panel"
        onMouseDown={mode === 'processed' ? handleImageMouseDown : undefined}
        onClick={mode === 'processed' ? handleBackgroundClick : undefined}
        onScroll={
          panelRef
            ? (e) => handleComparePanelScroll(e, panelRef)
            : undefined
        }
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
          minHeight: 0,
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
              ref={mode === 'original' ? imageRefOriginal : imageRefProcessed}
              src={getImageUrl(currentPage, mode)}
              alt={`第 ${currentPage.page_number} 页 - ${mode === 'original' ? '原图' : '处理后'}`}
              style={{
                maxWidth: 'none',
                display: 'block',
              }}
              draggable={false}
            />
            {showOverlayHere && (
              <div className="layout-overlay">
                {elements.map(renderElementBox)}
                {renderSplitLine()}
              </div>
            )}
          </div>
        ) : (
          <Empty description="请选择页面" />
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
        <Space wrap>
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

          {!compareMode && (
            <Select
              size="small"
              value={viewMode}
              onChange={setViewMode}
              style={{ width: 120 }}
            >
              <Option value="processed">处理后图像</Option>
              <Option value="original">原始图像</Option>
            </Select>
          )}

          <Tooltip title={compareMode ? '退出对比模式' : '对比模式：原图 vs 处理后'}>
            <Button
              size="small"
              type={compareMode ? 'primary' : 'default'}
              icon={<ColumnWidthOutlined />}
              onClick={() => setCompareMode(!compareMode)}
            >
              {compareMode ? '退出对比' : '对比模式'}
            </Button>
          </Tooltip>

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

          <Space.Split />

          <Tooltip title="合并选中的区域（按住Ctrl点击选择多个）">
            <Button
              size="small"
              icon={<MergeOutlined />}
              onClick={handleMerge}
              disabled={selectedElementIds.length < 2}
              type={selectedElementIds.length >= 2 ? 'primary' : 'default'}
            >
              合并{selectedElementIds.length >= 2 ? `(${selectedElementIds.length})` : ''}
            </Button>
          </Tooltip>

          <Tooltip title={splitMode ? '退出拆分模式' : '拆分选中的区域'}>
            <Button
              size="small"
              icon={<SplitCellsOutlined />}
              onClick={handleToggleSplitMode}
              type={splitMode ? 'primary' : 'default'}
              danger={splitMode}
              disabled={!selectedElementId}
            >
              {splitMode ? '退出拆分' : '拆分'}
            </Button>
          </Tooltip>

          {splitMode && (
            <Tag color="red">
              <CloseOutlined style={{ marginRight: 4 }} />
              拆分模式：在选中区域内拖动鼠标绘制分割线
            </Tag>
          )}

          <Space style={{ marginLeft: 'auto' }}>
            <span style={{ fontSize: 12, color: '#666' }}>
              共 {elements.length} 个元素
              {selectedElementIds.length > 0 && ` | 已选 ${selectedElementIds.length} 个（按住Ctrl多选）`}
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

        {compareMode ? (
          <div
            style={{
              flex: 1,
              display: 'flex',
              gap: 12,
              minHeight: 0,
            }}
          >
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
              <div
                style={{
                  textAlign: 'center',
                  padding: '4px 8px',
                  background: '#f5f5f5',
                  borderRadius: '4px 4px 0 0',
                  fontSize: 12,
                  color: '#666',
                  fontWeight: 'bold',
                }}
              >
                原始图像
              </div>
              {renderImagePanel('original', leftPanelRef)}
            </div>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
              <div
                style={{
                  textAlign: 'center',
                  padding: '4px 8px',
                  background: '#e6f7ff',
                  borderRadius: '4px 4px 0 0',
                  fontSize: 12,
                  color: '#1890ff',
                  fontWeight: 'bold',
                }}
              >
                处理后图像
              </div>
              {renderImagePanel('processed', rightPanelRef)}
            </div>
          </div>
        ) : (
          <div
            ref={containerRef}
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
              minHeight: 0,
            }}
            onMouseDown={handleImageMouseDown}
            onClick={handleBackgroundClick}
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
                    {renderSplitLine()}
                  </div>
                )}
              </div>
            ) : (
              <Empty description="请选择页面" />
            )}
          </div>
        )}

        <div
          className="elements-panel"
          style={{
            width: 340,
            background: '#fff',
            borderRadius: 8,
            padding: 16,
            overflowY: 'auto',
            flexShrink: 0,
          }}
        >
          <div style={{ fontWeight: 'bold', marginBottom: 12, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Space>
              <OrderedListOutlined />
              <span>元素列表</span>
            </Space>
            <Tag color="blue">{elements.length}</Tag>
          </div>

          <div style={{ fontSize: 11, color: '#999', marginBottom: 12, padding: '6px 8px', background: '#f5f5f5', borderRadius: 4 }}>
            <HolderOutlined style={{ marginRight: 4 }} />
            提示：按住左侧手柄上下拖动可调整阅读顺序
          </div>

          <List
            size="small"
            dataSource={sortedByOrder}
            renderItem={(elem) => {
              const color = getElementColor(elem.element_type);
              const isSelected = elem.id === selectedElementId;
              const isDragging = dragItemId === elem.id;
              const isDragOver = dragOverItemId === elem.id;

              return (
                <List.Item
                  className={`element-item ${isSelected ? 'selected' : ''} ${isDragging ? 'dragging' : ''} ${isDragOver ? 'drag-over' : ''}`}
                  style={{
                    cursor: 'pointer',
                    padding: '6px 8px',
                    borderRadius: 4,
                    marginBottom: 4,
                    background: isSelected ? '#e6f7ff' : isDragOver ? '#f6ffed' : 'transparent',
                    border: isDragOver ? '1px dashed #52c41a' : '1px solid transparent',
                    opacity: isDragging ? 0.5 : 1,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4,
                  }}
                  draggable
                  onDragStart={(e) => handleDragStart(e, elem.id)}
                  onDragOver={(e) => handleDragOver(e, elem.id)}
                  onDragLeave={handleDragLeave}
                  onDrop={(e) => handleDrop(e, elem.id)}
                  onDragEnd={handleDragEnd}
                  onClick={() => {
                    setSelectedElementId(elem.id);
                    setSelectedElementIds([elem.id]);
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
                  <div
                    style={{
                      cursor: 'grab',
                      padding: '0 4px',
                      color: '#999',
                      userSelect: 'none',
                      flexShrink: 0,
                    }}
                    onMouseDown={(e) => e.stopPropagation()}
                  >
                    <HolderOutlined />
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, width: '100%', minWidth: 0 }}>
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
                    <div style={{ fontSize: 11, color: '#999', flexShrink: 0 }}>
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
