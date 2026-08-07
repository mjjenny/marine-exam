import BookCover from "./BookCover.jsx";

/**
 * Static library bookshelf for the home page.
 * No scroll-linked motion — books sit on shelves and only lift on hover/focus.
 */
export default function Bookshelf({ subjects, onOpen }) {
  if (!subjects?.length) return null;

  return (
    <section
      className="bookshelf"
      aria-label="Subject library"
      data-testid="bookshelf"
    >
      <div className="bookshelf-inner">
        <ul className="bookshelf-grid" role="list">
          {subjects.map((s) => (
            <li key={s.slug} className="bookshelf-slot">
              <BookCover subject={s} onClick={() => onOpen(s)} />
              <span className="bookshelf-plank" aria-hidden="true" />
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
