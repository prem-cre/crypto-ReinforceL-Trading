import React from 'react';
import { Card, Tag, Typography, Space, Divider, Tooltip } from 'antd';
import { LinkOutlined, RobotOutlined, AlertOutlined } from '@ant-design/icons';
import type { SignalCitation } from '../types/trading';

const { Text, Paragraph } = Typography;

interface Props {
  rationale?: string;
  citations?: SignalCitation[];
  sentiment_score?: number;
}

function SentimentBadge({ score }: { score: number }) {
  let color: string;
  let label: string;
  if (score >= 0.4) { color = '#52c41a'; label = 'Bullish'; }
  else if (score >= 0.1) { color = '#95de64'; label = 'Slightly Bullish'; }
  else if (score > -0.1) { color = '#faad14'; label = 'Neutral'; }
  else if (score > -0.4) { color = '#ff7875'; label = 'Slightly Bearish'; }
  else { color = '#cf1322'; label = 'Bearish'; }

  const pct = Math.round(Math.abs(score) * 100);
  return (
    <Tooltip title={`Sentiment: ${score.toFixed(2)}`}>
      <Tag color={color} style={{ fontWeight: 600 }}>
        {label} ({pct}%)
      </Tag>
    </Tooltip>
  );
}

export const SignalRationale: React.FC<Props> = ({ rationale, citations, sentiment_score }) => {
  if (!rationale && (citations == null || citations.length === 0)) {
    return null;
  }

  return (
    <Card
      size="small"
      style={{ marginTop: 12, background: 'rgba(0,0,0,0.02)', borderLeft: '3px solid #1677ff' }}
      bodyStyle={{ padding: '12px 16px' }}
    >
      <Space direction="vertical" size={8} style={{ width: '100%' }}>
        {/* Header row */}
        <Space>
          <RobotOutlined style={{ color: '#1677ff' }} />
          <Text strong style={{ fontSize: 13 }}>AI Analysis</Text>
          {sentiment_score != null && <SentimentBadge score={sentiment_score} />}
        </Space>

        {/* Rationale */}
        {rationale && (
          <Paragraph
            style={{ margin: 0, fontSize: 13, color: '#555' }}
            ellipsis={{ rows: 3, expandable: true, symbol: 'more' }}
          >
            {rationale}
          </Paragraph>
        )}

        {/* Citations */}
        {citations && citations.length > 0 && (
          <>
            <Divider style={{ margin: '6px 0' }} />
            <Space wrap size={4}>
              <AlertOutlined style={{ color: '#999', fontSize: 11 }} />
              <Text type="secondary" style={{ fontSize: 11 }}>Sources:</Text>
              {citations.map((c, i) => (
                <a key={i} href={c.url} target="_blank" rel="noopener noreferrer">
                  <Tag
                    icon={<LinkOutlined />}
                    style={{ fontSize: 11, cursor: 'pointer', marginBottom: 2 }}
                  >
                    {c.title || c.source || new URL(c.url).hostname}
                  </Tag>
                </a>
              ))}
            </Space>
          </>
        )}
      </Space>
    </Card>
  );
};

export default SignalRationale;
