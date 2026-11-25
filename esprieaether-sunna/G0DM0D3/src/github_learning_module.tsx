// G0DM0D3 GitHub Learning Integration Module
// Connects G0DM0D3 with GitHub repositories for autonomous learning

import { useState } from 'react';

interface Repository {
  full_name: string;
  description: string;
  stargazers_count: number;
  forks_count: number;
  language: string;
  topics: string[];
  score: number;
  categories: string[];
  learning_opportunities: string[];
}

interface GitHubIntegration {
  token?: string;
  searchRepositories(query: string, limit: number, sort: string): Promise<Repository[]>;
  getRepository(repoName: string): Promise<Repository | null>;
  getRepositoryContents(repoName: string, path: string): Promise<string[]>;
  analyzeRepository(repo: any): Repository;
  searchLearningPaths(queries: string[]): Promise<any[]>;
}

export function GitHubLearningModule({ token }: { token?: string }) {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedRepo, setSelectedRepo] = useState<Repository | null>(null);
  const [activeCategory, setActiveCategory] = useState<string>('automation');

  const categories = [
    'automation',
    'security', 
    'ai-ml',
    'reverse-engineering',
    'education'
  ];

  const searchRepositories = async (query: string, limit = 20) => {
    if (!token) {
      alert('⚠️ Please set GITHUB_TOKEN in your environment variables');
      return;
    }

    setLoading(true);
    try {
      // This would call the GitHub API integration
      // API_URL = '/api/github/search'
      // const response = await fetch(`${API_URL}?q=${encodeURIComponent(query)}&limit=${limit}`, {
      //   headers: { 'Authorization': `token ${token}` }
      // });
      // const data = await response.json();
      // setRepositories(data.items || []);
      
      // Demo data for now
      const demoData = [
        {
          full_name: 'CarterPerez-dev/Cybersecurity-Projects',
          description: 'Building 70 Cybersecurity Projects from beginner to advanced',
          stargazers_count: 8400,
          forks_count: 2000,
          language: 'Python',
          topics: ['cybersecurity', 'automation', 'education'],
          score: 95,
          categories: ['security', 'automation', 'education'],
          learning_opportunities: ['python-scripts', 'security-patterns', 'automation-patterns']
        },
        {
          full_name: 'AndrejG03/100-days-of-cybersecurity',
          description: '100 days of cybersecurity projects and challenges',
          stargazers_count: 3500,
          forks_count: 800,
          language: 'Python',
          topics: ['cybersecurity', 'learning', 'reversing'],
          score: 90,
          categories: ['security', 'education', 'reverse-engineering'],
          learning_opportunities: ['security-patterns', 'reversing', 'network-analysis']
        }
      ];
      setRepositories(demoData);
    } catch (error: any) {
      console.error('Error searching repos:', error);
      alert('Error searching GitHub repositories');
    } finally {
      setLoading(false);
    }
  };

  const analyzeRepository = (repo: Repository) => {
    return {
      ...repo,
      score: repo.stargazers_count / 100 + repo.forks_count / 50,
      categories: repo.topics.map(t =>
        t.toLowerCase().includes('automation') ? 'automation' :
        t.toLowerCase().includes('security') ? 'security' :
        t.toLowerCase().includes('ai') ? 'ai-ml' :
        t.toLowerCase().includes('reverse') ? 'reverse-engineering' : 'general'
      ),
      learning_opportunities: [
        'python-scripts',
        'security-patterns',
        'automation-patterns',
        'ai-patterns',
        'reversing'
      ]
    };
  };

  const saveToLearningPath = (repo: Repository) => {
    // Save to learning path database
    // POST /api/github/learning/add
    console.log(`🧠 Saved to learning path: ${repo.full_name}`);
  };

  return (
    <div className="github-learning-module">
      <h2>🐙 G0DM0D3 + GitHub Integration</h2>
      
      <div className="module-header">
        <h3>🔍 Search GitHub Repositories</h3>
        <div className="search-controls">
          <input
            type="text"
            placeholder="Search repositories (e.g. 'machine learning automation')..."
            onChange={(e) => {
              // Search functionality
            }}
            className="search-input"
          />
          <button
            onClick={() => searchRepositories('machine learning')}>
            Search
          </button>
        </div>
        <div className="categories">
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`category-btn ${activeCategory === cat ? 'active' : ''}`}>
              {cat}
            </button>
          ))}
        </div>
      </div>

      <div className="repositories-grid">
        {repositories.map(repo => (
          <div key={repo.full_name} className="repo-card">
            <div className="repo-header">
              <h4>{repo.full_name}</h4>
              <span className="repo-star">⭐ {repo.stargazers_count}</span>
            </div>
            <p>{repo.description}</p>
            
            <div className="repo-tags">
              {repo.language && <span className="tag">{repo.language}</span>}
              {repo.categories.map(cat => (
                <span key={cat} className="tag">{cat}</span>
              ))}
            </div>
            
            <div className="repo-metadata">
              <p>⭐ {repo.stargazers_count} | 🌿 {repo.forks_count}</p>
              <p>Learning: {repo.learning_opportunities.join(', ')}</p>
            </div>
            
            <button
              onClick={() => {
                setSelectedRepo(repo);
                saveToLearningPath(repo);
              }}
              className="learning-btn">
              🎓 Add to Learning Path
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default GitHubLearningModule;
