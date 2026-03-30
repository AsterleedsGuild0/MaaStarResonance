import Layout from '@theme/Layout';
import styles from './index.module.css';

function Home() {
  return (
    <Layout title="MaaStarResonance" description="基于MAAFW的星痕共鸣黑盒测试工具" wrapperClassName="home-page">
      <div className={styles.hero} >
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', padding: '2rem' }}>
          {/* 主视觉区 */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', maxWidth: '2000px', margin: '0 auto' }}>
            {/* 左侧文字区 */}
            <div style={{ textAlign: 'left', flex: 1, padding: '0 2rem' }}>
              <h1 style={{
                fontSize: '4.5rem',
                fontWeight: 'bold',
                backgroundImage: 'linear-gradient(135deg, #996dff, #7f8cff, #4e8dff)',
                WebkitBackgroundClip: 'text',
                backgroundClip: 'text',
                color: 'transparent',
                textShadow: '0 0 10px rgba(108, 92, 231, 0.25)',
                marginBottom: '1rem',
              }}>
                星痕共鸣 Maa 小助手
              </h1>
              <p style={{ fontSize: '1.5rem', color: '#7e7d7dff', marginBottom: '1rem' }}>
                基于MAAFW的星痕共鸣黑盒测试工具
              </p>
              <div style={{ display: 'flex', gap: '1rem' }}>
                <a
                  href="/docs/用户文档/新手上路"
                  style={{
                    backgroundImage: 'linear-gradient(135deg, #996dff, #7f8cff, #4e8dff)',
                    color: 'white',
                    padding: '0.75rem 1.5rem',
                    borderRadius: '999px',
                    fontSize: '1rem',
                    fontWeight: 'bold',
                    textDecoration: 'none',
                    boxShadow: '0 4px 10px rgba(87, 74, 255, 0.35)',
                    transition: 'all 0.3s ease',
                    border: 'none',
                  }}
                  onMouseEnter={(e) => {
                    e.target.style.transform = 'translateY(-2px)';
                    e.target.style.boxShadow = '0 8px 18px rgba(87, 74, 255, 0.45)';
                    e.target.style.filter = 'brightness(1.05)';
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.transform = 'translateY(0)';
                    e.target.style.boxShadow = '0 4px 10px rgba(87, 74, 255, 0.35)';
                    e.target.style.filter = 'brightness(1)';
                  }}
                >
                  快速开始
                </a>
                <a
                  href="https://github.com/AsterleedsGuild0/MaaStarResonance"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    position: 'relative',
                    padding: '0.75rem 1.5rem',
                    borderRadius: '999px',
                    fontSize: '1rem',
                    fontWeight: 'bold',
                    textDecoration: 'none',
                    color: '#996dff',
                    backgroundColor: 'transparent',
                    border: '2px solid transparent',
                    backgroundImage: 'linear-gradient(#fff, #fff), linear-gradient(135deg, #996dff, #7f8cff, #4e8dff)',
                    backgroundOrigin: 'border-box',
                    backgroundClip: 'padding-box, border-box',
                    transition: 'all 0.3s ease',
                    boxShadow: '0 4px 10px rgba(0, 0, 0, 0.08)',
                  }}
                  onMouseEnter={(e) => {
                    e.target.style.transform = 'translateY(-2px)';
                    e.target.style.boxShadow = '0 8px 18px rgba(0, 0, 0, 0.15)';
                    e.target.style.color = '#4e8dff';
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.transform = 'translateY(0)';
                    e.target.style.boxShadow = '0 4px 10px rgba(0, 0, 0, 0.08)';
                    e.target.style.color = '#996dff';
                  }}
                >
                  查看 GitHub
                </a>
              </div>
            </div>

            {/* 右侧图片区 */}
            <div style={{ flex: 1, textAlign: 'center' }}>
              <img
                src="img/logo_transparent.png"
                alt="MaaStarResonance Image"
                style={{
                  maxWidth: '50%',
                  height: 'auto',
                  borderRadius: '12px',
                  transition: 'transform 0.3s ease',
                }}
                onMouseEnter={(e) => {
                  e.target.style.transform = 'scale(1.05)';
                }}
                onMouseLeave={(e) => {
                  e.target.style.transform = 'scale(1)';
                }}
              />
            </div>
          </div>
          
        </div>
      </div>
    </Layout>
  );
}

export default Home;
